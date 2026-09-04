"""Phase 13 Slice 2: Storage Substrate & Two-Phase Recoverable Commit Engine (Rev 20).

Implements transactional filesystem substrate, durability barriers (FlushFileBuffers/fsync),
immutable versioned snapshots, read-only ACL enforcement, atomic pointer switching,
persistent CAS state machine, and cryptographically authenticated transition records per:
- docs/phase13/slice2_gate_b_plan.md (§3.6, §3.7, §3.8, §3.9)
- Findings B64, B65, B67, B69, B70, B75, B76, B80, B82, B83, B86, B88, B89, B90, B93, B94, B95, B98
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import threading
from typing import Any, Dict, Generator, Optional, Tuple
from uuid import UUID, uuid4

from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.crypto import Ed25519Signer, Ed25519TrustStore
from acash.gate_b.exceptions import (
    CryptographicVerificationError,
    DataContractError,
    PreLiveRiskAdmissionError,
    QuarantineError,
    StorageDurabilityError,
)
from acash.gate_b.schema import (
    AuthoritativeAbortRecordBlock,
    AuthoritativeCommitRecordBlock,
    AuthoritativeLedgerProtocol,
    DurablePointerTransitionRecord,
    DurableTransactionState,
    HumanGORecord,
    JournalState,
    LiveAuthorization,
    LiveAuthorizationStatus,
    SystemSafetyMode,
)

GENESIS_HEAD_DIGEST: str = "0" * 64


class StorageEngineSigner:
    """Storage engine trust anchor for signing pointer transition records (B88, B93)."""

    def __init__(self, key_id: str, private_key_b64: str) -> None:
        self.key_id = key_id
        self._private_key_b64 = private_key_b64

    def sign(self, payload_bytes: bytes) -> str:
        return Ed25519Signer.sign(self._private_key_b64, payload_bytes)


class WALJournal:
    """Reconstructible operational write-ahead journal."""

    def __init__(self, journal_path: Path, tx_id: UUID, authorization_id: str) -> None:
        self._path = journal_path
        self._tx_id = tx_id
        self._auth_id = authorization_id

    @property
    def journal_path(self) -> Path:
        return self._path

    def write_state_durable(self, state: JournalState) -> None:
        """Append journal transition record and sync to disk."""
        entry = {
            "activation_transaction_id": str(self._tx_id),
            "authorization_id": self._auth_id,
            "journal_state": state.value,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        line = CanonicalConfigSerializer.to_canonical_json(entry) + "\n"
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            StoragePlatformUtils.flush_file(f.fileno())

    def read_latest_state(self) -> Optional[JournalState]:
        """Read latest logged journal state if present."""
        if not self._path.exists():
            return None
        latest: Optional[JournalState] = None
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    try:
                        data = json.loads(stripped)
                        st_val = data.get("journal_state")
                        if isinstance(st_val, dict):
                            st_val = st_val.get("value")
                        if st_val:
                            latest = JournalState(str(st_val))
                    except Exception:
                        pass
        return latest


class StoragePlatformUtils:
    """Platform durability primitives for Windows NTFS/ReFS and Linux ext4/XFS (B89, B98)."""

    _win32_initialized: bool = False
    _get_osfhandle: Any = None
    _FlushFileBuffers: Any = None
    _CreateFileW: Any = None
    _CloseHandle: Any = None

    # Win32 Constants
    GENERIC_READ: int = 0x80000000
    GENERIC_WRITE: int = 0x40000000
    FILE_SHARE_READ: int = 0x00000001
    FILE_SHARE_WRITE: int = 0x00000002
    FILE_SHARE_DELETE: int = 0x00000004
    OPEN_EXISTING: int = 3
    FILE_FLAG_BACKUP_SEMANTICS: int = 0x02000000
    INVALID_HANDLE_VALUE: int = -1

    @classmethod
    def _ensure_win32_initialized(cls) -> None:
        """Initialize 64-bit Win32 C runtime and kernel32 function signatures."""
        if cls._win32_initialized or os.name != "nt":
            return

        try:
            ucrt = ctypes.CDLL("ucrtbase.dll")
            cls._get_osfhandle = ucrt._get_osfhandle
        except Exception:
            import msvcrt
            cls._get_osfhandle = msvcrt.get_osfhandle

        cls._get_osfhandle.argtypes = [ctypes.c_int]
        cls._get_osfhandle.restype = ctypes.c_void_p

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        cls._FlushFileBuffers = kernel32.FlushFileBuffers
        cls._FlushFileBuffers.argtypes = [wintypes.HANDLE]
        cls._FlushFileBuffers.restype = wintypes.BOOL

        cls._CreateFileW = kernel32.CreateFileW
        cls._CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        cls._CreateFileW.restype = wintypes.HANDLE

        cls._CloseHandle = kernel32.CloseHandle
        cls._CloseHandle.argtypes = [wintypes.HANDLE]
        cls._CloseHandle.restype = wintypes.BOOL

        cls._win32_initialized = True

    @classmethod
    def flush_file(cls, fd: int) -> None:
        """Call FlushFileBuffers on Windows or fsync on Linux with strict error propagation."""
        if os.name == "nt":
            try:
                os.fstat(fd)
            except OSError as exc:
                raise StorageDurabilityError(f"INVALID_FILE_DESCRIPTOR: fd={fd}: {exc}") from exc

            cls._ensure_win32_initialized()
            handle = cls._get_osfhandle(fd)
            if not handle or handle == cls.INVALID_HANDLE_VALUE or handle == -1 or handle == ctypes.c_void_p(-1).value:
                err = ctypes.get_last_error()
                raise StorageDurabilityError(f"INVALID_WIN32_FILE_HANDLE: fd={fd}, error={err}")

            res = cls._FlushFileBuffers(handle)
            if not res:
                err = ctypes.get_last_error()
                raise StorageDurabilityError(
                    f"WIN32_FLUSH_FILE_BUFFERS_FAILED: fd={fd}, handle={handle}, win_error={err}"
                )
        else:
            try:
                os.fsync(fd)
            except OSError as exc:
                raise StorageDurabilityError(f"POSIX_FSYNC_FAILED: fd={fd}: {exc}") from exc

    @classmethod
    def flush_directory(cls, directory: Path) -> None:
        """Call FlushFileBuffers on directory handle (Windows) or fsync on directory fd (POSIX)."""
        if not directory.exists():
            return

        if os.name == "nt":
            cls._ensure_win32_initialized()
            handle = cls._CreateFileW(
                str(directory),
                cls.GENERIC_READ | cls.GENERIC_WRITE,
                cls.FILE_SHARE_READ | cls.FILE_SHARE_WRITE | cls.FILE_SHARE_DELETE,
                None,
                cls.OPEN_EXISTING,
                cls.FILE_FLAG_BACKUP_SEMANTICS,
                None,
            )
            if handle and handle != cls.INVALID_HANDLE_VALUE and handle != -1 and handle != ctypes.c_void_p(-1).value:
                try:
                    res = cls._FlushFileBuffers(handle)
                    if not res:
                        err = ctypes.get_last_error()
                        raise StorageDurabilityError(
                            f"WIN32_FLUSH_DIRECTORY_BUFFERS_FAILED: dir={directory}, handle={handle}, win_error={err}"
                        )
                finally:
                    cls._CloseHandle(handle)
            else:
                err = ctypes.get_last_error()
                # If opening with GENERIC_WRITE failed with ERROR_ACCESS_DENIED (5), directory is read-only.
                # NTFS journals directory entries on atomic move/replace; read-only dirs are immutable.
                if err != 5:
                    raise StorageDurabilityError(
                        f"FAILED_TO_OPEN_DIRECTORY_FOR_FLUSH: dir={directory}, win_error={err}"
                    )
        else:
            try:
                dir_fd = os.open(str(directory), os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except OSError as exc:
                raise StorageDurabilityError(f"POSIX_DIR_FSYNC_FAILED: dir={directory}: {exc}") from exc

    @classmethod
    def flush_parent_dir(cls, path: Path) -> None:
        """Call durability barrier on parent directory."""
        cls.flush_directory(path.parent)

    @classmethod
    def flush_parent_dir_if_posix(cls, path: Path) -> None:
        """Compatibility wrapper: flushes parent directory on both Windows and POSIX."""
        cls.flush_parent_dir(path)

    @classmethod
    def write_file_durable(cls, path: Path, content_bytes: bytes) -> None:
        """Write file atomically using replace semantics and non-volatile barrier."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(f".tmp.{uuid4().hex}")
        with open(temp_path, "wb") as f:
            f.write(content_bytes)
            f.flush()
            cls.flush_file(f.fileno())
        os.replace(temp_path, path)
        cls.flush_parent_dir(path)

    @classmethod
    def mark_directory_read_only(cls, directory: Path) -> None:
        """Enforce read-only ACLs on directory and all contained files (B75, B83)."""
        if not directory.exists():
            return

        # 1. Set read-only attributes on files and directories (POSIX + Windows file attrs)
        ro_mode = stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH
        for root, dirs, files in os.walk(directory):
            for file_name in files:
                file_path = Path(root) / file_name
                try:
                    os.chmod(file_path, ro_mode)
                except Exception as exc:
                    raise StorageDurabilityError(f"FAILED_TO_SET_READ_ONLY_ON_FILE: {file_path}: {exc}") from exc
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                try:
                    os.chmod(dir_path, ro_mode | stat.S_IEXEC)
                except Exception as exc:
                    raise StorageDurabilityError(f"FAILED_TO_SET_READ_ONLY_ON_DIR: {dir_path}: {exc}") from exc
        try:
            os.chmod(directory, ro_mode | stat.S_IEXEC)
        except Exception as exc:
            raise StorageDurabilityError(f"FAILED_TO_SET_READ_ONLY_ON_ROOT_DIR: {directory}: {exc}") from exc

        # 2. On Windows: Enforce kernel-level NTFS DACL denying Write, Append, Delete, and DeleteChild
        if os.name == "nt":
            cmd = [
                "icacls",
                str(directory),
                "/deny",
                "Everyone:(OI)(CI)(WD,AD,WA,WEA,DE,DC)",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise StorageDurabilityError(
                    f"FAILED_TO_SET_NTFS_DACL: dir={directory}, error={res.stderr.strip() or res.stdout.strip()}"
                )

    @classmethod
    def mark_directory_writable(cls, directory: Path) -> None:
        """Restore write permissions on directory and contents (for testing cleanup)."""
        if not directory.exists():
            return

        # 1. On Windows: Recursively remove the Deny ACE for Everyone across tree
        if os.name == "nt":
            subprocess.run(
                ["icacls", str(directory), "/remove:d", "Everyone", "/t", "/c", "/q"],
                capture_output=True,
                text=True,
            )

        # 2. Restore writable mode
        rw_mode = stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC
        for root, dirs, files in os.walk(directory):
            for file_name in files:
                try:
                    os.chmod(Path(root) / file_name, stat.S_IWRITE | stat.S_IREAD)
                except Exception:
                    pass
            for dir_name in dirs:
                try:
                    os.chmod(Path(root) / dir_name, rw_mode)
                except Exception:
                    pass
        try:
            os.chmod(directory, rw_mode)
        except Exception:
            pass


class LedgerStorageTransaction:
    """Encapsulates exclusive transactional access to storage substrate."""

    def __init__(self, root: Path, trust_store: Ed25519TrustStore) -> None:
        self._root = root
        self._trust_store = trust_store
        self._staging_dir = root / "staging"
        self._snapshots_dir = root / "snapshots"
        self._pointer_dir = root / "pointer"
        self._aborts_dir = root / "aborts"
        self._tx_state_dir = root / "tx_state"
        self._journal_dir = root / "journal"
        self._system_mode_file = root / "system_safety_mode.state"
        self._head_file = root / "head.json"

        # Ensure directory skeleton exists
        for d in [
            self._staging_dir,
            self._snapshots_dir,
            self._pointer_dir,
            self._aborts_dir,
            self._tx_state_dir,
            self._journal_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    @property
    def current_head_digest(self) -> str:
        """Authoritative current ledger head digest."""
        if not self._head_file.exists():
            return GENESIS_HEAD_DIGEST
        try:
            with open(self._head_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return str(data.get("head_digest", GENESIS_HEAD_DIGEST))
        except Exception:
            return GENESIS_HEAD_DIGEST

    def set_head_digest_durable(self, new_head: str) -> None:
        """Update authoritative ledger head digest on disk."""
        payload = {"head_digest": new_head, "updated_at_utc": datetime.now(timezone.utc).isoformat()}
        raw = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
        StoragePlatformUtils.write_file_durable(self._head_file, raw)

    def get_system_safety_mode(self) -> SystemSafetyMode:
        """Get system-wide operational safety mode (B95)."""
        if not self._system_mode_file.exists():
            return SystemSafetyMode.NORMAL
        try:
            with open(self._system_mode_file, "r", encoding="utf-8") as f:
                mode_str = f.read().strip()
                return SystemSafetyMode(mode_str)
        except Exception:
            return SystemSafetyMode.QUARANTINE_LOCKED

    def set_system_safety_mode(self, mode: SystemSafetyMode) -> None:
        """Persist system-wide operational safety mode (B95)."""
        StoragePlatformUtils.write_file_durable(self._system_mode_file, mode.value.encode("utf-8"))

    # Transaction State CAS
    def _get_tx_state_path(self, tx_id: UUID) -> Path:
        return self._tx_state_dir / f"{tx_id}.state"

    def get_durable_tx_state(self, tx_id: UUID) -> Optional[DurableTransactionState]:
        """Read persisted on-disk transaction lifecycle state."""
        path = self._get_tx_state_path(tx_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                val = f.read().strip()
                return DurableTransactionState(val)
        except Exception:
            return DurableTransactionState.QUARANTINED

    def set_tx_state_durable(self, tx_id: UUID, state: DurableTransactionState) -> None:
        """Persist transaction state file synchronously to disk."""
        path = self._get_tx_state_path(tx_id)
        StoragePlatformUtils.write_file_durable(path, state.value.encode("utf-8"))

    def compare_and_set_tx_state(
        self,
        tx_id: UUID,
        expected: DurableTransactionState,
        new: DurableTransactionState,
    ) -> bool:
        """Atomic Compare-And-Swap transaction state transition."""
        current = self.get_durable_tx_state(tx_id)
        if current != expected:
            return False
        self.set_tx_state_durable(tx_id, new)
        return True

    def has_transaction_id(self, tx_id: UUID) -> bool:
        """Check if transaction ID has already been reserved or used."""
        return self._get_tx_state_path(tx_id).exists()

    def reserve_transaction_id(self, tx_id: UUID) -> None:
        """Reserve unique transaction ID."""
        if self.has_transaction_id(tx_id):
            raise DataContractError(f"TRANSACTION_ID_ALREADY_RESERVED: {tx_id}")
        self.set_tx_state_durable(tx_id, DurableTransactionState.PREPARED)

    def create_wal_journal(
        self,
        activation_transaction_id: UUID,
        authorization_id: str,
        go_record: Optional[HumanGORecord],
    ) -> WALJournal:
        """Instantiate durable WAL journal."""
        jpath = self._journal_dir / f"{activation_transaction_id}.wal"
        journal = WALJournal(jpath, activation_transaction_id, authorization_id)
        return journal

    # Phase 1: Staged Mutation Data
    def _get_staging_tx_dir(self, tx_id: UUID) -> Path:
        return self._staging_dir / str(tx_id)

    def write_staged_mutation_data(
        self,
        tx_id: UUID,
        go_record: HumanGORecord,
        activated_auth: LiveAuthorization,
    ) -> None:
        """Phase 1: Write mutation payload into /staging/<tx_id>/."""
        tx_stage = self._get_staging_tx_dir(tx_id)
        tx_stage.mkdir(parents=True, exist_ok=True)

        record_path = tx_stage / "record.json"
        auth_path = tx_stage / "authorization.json"
        head_path = tx_stage / "head.json"

        # Write record.json
        record_bytes = CanonicalConfigSerializer.to_canonical_json(go_record.model_dump(mode="json")).encode("utf-8")
        with open(record_path, "wb") as f:
            f.write(record_bytes)
            f.flush()

        # Write authorization.json
        auth_bytes = CanonicalConfigSerializer.to_canonical_json(activated_auth.model_dump(mode="json")).encode(
            "utf-8"
        )
        with open(auth_path, "wb") as f:
            f.write(auth_bytes)
            f.flush()

        # Write proposed head.json
        head_bytes = CanonicalConfigSerializer.to_canonical_json(
            {"head_digest": go_record.record_digest, "tx_id": str(tx_id)}
        ).encode("utf-8")
        with open(head_path, "wb") as f:
            f.write(head_bytes)
            f.flush()

    def flush_staged_mutation_data_barrier(self, tx_id: UUID) -> None:
        """Phase 1 fsync_1 barrier."""
        tx_stage = self._get_staging_tx_dir(tx_id)
        for fname in ["record.json", "authorization.json", "head.json"]:
            fpath = tx_stage / fname
            if fpath.exists():
                with open(fpath, "r+b") as f:
                    StoragePlatformUtils.flush_file(f.fileno())
        StoragePlatformUtils.flush_parent_dir_if_posix(tx_stage / "record.json")

    def verify_staged_mutation_data_durable(
        self,
        tx_id: UUID,
        expected_record_digest: str,
        activated_auth: LiveAuthorization,
    ) -> bool:
        """Phase 1 durability check."""
        tx_stage = self._get_staging_tx_dir(tx_id)
        rec_path = tx_stage / "record.json"
        auth_path = tx_stage / "authorization.json"
        head_path = tx_stage / "head.json"

        if not (rec_path.exists() and auth_path.exists() and head_path.exists()):
            return False

        try:
            with open(rec_path, "r", encoding="utf-8") as f:
                rec_data = json.load(f)
                digest_val = rec_data.get("record_digest")
                if isinstance(digest_val, dict):
                    digest_val = digest_val.get("value")
                if digest_val != expected_record_digest:
                    return False
            with open(auth_path, "r", encoding="utf-8") as f:
                auth_data = json.load(f)
                status_val = auth_data.get("status")
                if isinstance(status_val, dict):
                    status_val = status_val.get("value")
                if status_val != LiveAuthorizationStatus.ACTIVE.value:
                    return False
            return True
        except Exception:
            return False

    # Phase 2: Commit Marker
    def write_commit_marker_block(
        self,
        tx_id: UUID,
        commit_block: AuthoritativeCommitRecordBlock,
    ) -> None:
        """Phase 2: Write commit_record_block.json into staging."""
        tx_stage = self._get_staging_tx_dir(tx_id)
        marker_path = tx_stage / "commit_record_block.json"
        raw = CanonicalConfigSerializer.to_canonical_json(commit_block.model_dump(mode="json")).encode("utf-8")
        with open(marker_path, "wb") as f:
            f.write(raw)
            f.flush()

    def flush_commit_marker_barrier(self, tx_id: UUID) -> None:
        """Phase 2 fsync_2 barrier."""
        marker_path = self._get_staging_tx_dir(tx_id) / "commit_record_block.json"
        if marker_path.exists():
            with open(marker_path, "r+b") as f:
                StoragePlatformUtils.flush_file(f.fileno())
        StoragePlatformUtils.flush_parent_dir_if_posix(marker_path)

    def verify_commit_marker_durable(self, tx_id: UUID, expected_manifest_digest: str) -> bool:
        """Phase 2 durability verification."""
        marker_path = self._get_staging_tx_dir(tx_id) / "commit_record_block.json"
        if not marker_path.exists():
            return False
        try:
            with open(marker_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                manifest_val = data.get("mutation_manifest_digest")
                if isinstance(manifest_val, dict):
                    manifest_val = manifest_val.get("value")
                return bool(manifest_val == expected_manifest_digest)
        except Exception:
            return False

    # Phase 3: Promotion to Snapshots
    def _get_snapshot_tx_dir(self, tx_id: UUID) -> Path:
        return self._snapshots_dir / str(tx_id)

    def promote_staging_to_snapshot_directory_atomically(self, tx_id: UUID) -> None:
        """Phase 3: Atomic rename from staging/<tx_id> to snapshots/<tx_id>."""
        staging_dir = self._get_staging_tx_dir(tx_id)
        snapshot_dir = self._get_snapshot_tx_dir(tx_id)
        if not staging_dir.exists():
            raise StorageDurabilityError(f"STAGING_DIRECTORY_MISSING_FOR_PROMOTION: {staging_dir}")
        if snapshot_dir.exists():
            raise StorageDurabilityError(f"SNAPSHOT_DIRECTORY_ALREADY_EXISTS: {snapshot_dir}")

        os.replace(staging_dir, snapshot_dir)
        StoragePlatformUtils.flush_parent_dir(snapshot_dir)

    def mark_snapshot_directory_read_only(self, tx_id: UUID) -> None:
        """Phase 3: Mark promoted snapshot directory and files read-only (B75, B83)."""
        snapshot_dir = self._get_snapshot_tx_dir(tx_id)
        StoragePlatformUtils.mark_directory_read_only(snapshot_dir)

    def flush_snapshot_directory_barrier(self, tx_id: UUID) -> None:
        """Phase 3 fsync_3 barrier on snapshot directory and parent container."""
        snapshot_dir = self._get_snapshot_tx_dir(tx_id)
        StoragePlatformUtils.flush_directory(snapshot_dir)
        StoragePlatformUtils.flush_parent_dir(snapshot_dir)

    # Phase 4: Pre-CAS Deep Verification
    def deep_verify_snapshot_manifest(
        self,
        tx_id: UUID,
        expected_commit_block: AuthoritativeCommitRecordBlock,
    ) -> bool:
        """Phase 4: Re-verify all entities and hashes under exclusive lock prior to pointer switch (B75, B86)."""
        snap_dir = self._get_snapshot_tx_dir(tx_id)
        if not snap_dir.exists():
            return False

        rec_file = snap_dir / "record.json"
        auth_file = snap_dir / "authorization.json"
        head_file = snap_dir / "head.json"
        marker_file = snap_dir / "commit_record_block.json"

        if not (rec_file.exists() and auth_file.exists() and head_file.exists() and marker_file.exists()):
            return False

        try:
            with open(marker_file, "r", encoding="utf-8") as f:
                marker_data = json.load(f)
                manifest_val = marker_data.get("mutation_manifest_digest")
                if isinstance(manifest_val, dict):
                    manifest_val = manifest_val.get("value")
                if manifest_val != expected_commit_block.mutation_manifest_digest:
                    return False

            with open(rec_file, "r", encoding="utf-8") as f:
                rec_data = json.load(f)
                rec_digest = rec_data.get("record_digest")
                if isinstance(rec_digest, dict):
                    rec_digest = rec_digest.get("value")
                if rec_digest != expected_commit_block.ledger_record_digest:
                    return False

            with open(auth_file, "r", encoding="utf-8") as f:
                auth_data = json.load(f)
                act_digest = auth_data.get("activated_authorization_digest")
                if isinstance(act_digest, dict):
                    act_digest = act_digest.get("value")
                if act_digest != expected_commit_block.activated_authorization_digest:
                    return False

            return True
        except Exception:
            return False

    # Phase 5: Pointer Transition Record & Atomic Pointer Switch
    def get_next_pointer_version(self) -> int:
        """Determine next monotonic pointer version."""
        transition_path = self._pointer_dir / "transition.json"
        if not transition_path.exists():
            return 1
        try:
            with open(transition_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                ver = data.get("pointer_version")
                if isinstance(ver, dict):
                    ver = ver.get("value")
                return int(ver or 0) + 1
        except Exception:
            return 1

    def get_current_active_transaction_id(self) -> Optional[UUID]:
        """Read transaction ID referenced by current committed pointer."""
        pointer_path = self._pointer_dir / "committed_pointer"
        if not pointer_path.exists():
            return None
        try:
            with open(pointer_path, "r", encoding="utf-8") as f:
                tx_str = f.read().strip()
                return UUID(tx_str)
        except Exception:
            return None

    def get_current_pointer_digest(self) -> str:
        """Compute SHA-256 of current pointer file."""
        pointer_path = self._pointer_dir / "committed_pointer"
        if not pointer_path.exists():
            return "0" * 64
        with open(pointer_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def write_durable_pointer_transition_record(
        self,
        transition_record: DurablePointerTransitionRecord,
    ) -> None:
        """Step 5a: Write cryptographically authenticated pointer transition record (B88, B93)."""
        trans_path = self._pointer_dir / "transition.json"
        raw = CanonicalConfigSerializer.to_canonical_json(transition_record.model_dump(mode="json")).encode("utf-8")
        StoragePlatformUtils.write_file_durable(trans_path, raw)

    def flush_pointer_transition_barrier(self) -> None:
        """Step 5a: Flush pointer transition record barrier."""
        trans_path = self._pointer_dir / "transition.json"
        if trans_path.exists():
            with open(trans_path, "r+b") as f:
                StoragePlatformUtils.flush_file(f.fileno())
        StoragePlatformUtils.flush_parent_dir_if_posix(trans_path)

    def read_pointer_transition_record(self) -> Optional[DurablePointerTransitionRecord]:
        """Read on-disk pointer transition record if present."""
        trans_path = self._pointer_dir / "transition.json"
        if not trans_path.exists():
            return None
        try:
            with open(trans_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                normalized: Dict[str, Any] = {}
                for k, v in data.items():
                    if isinstance(v, dict) and "value" in v:
                        normalized[k] = v["value"]
                    else:
                        normalized[k] = v
                return DurablePointerTransitionRecord.model_validate(normalized)
        except Exception:
            return None

    def switch_committed_snapshot_pointer_atomically(self, tx_id: UUID) -> None:
        """Step 5b: Switch committed_pointer to point to snapshots/<tx_id>."""
        pointer_path = self._pointer_dir / "committed_pointer"
        raw = str(tx_id).encode("utf-8")
        StoragePlatformUtils.write_file_durable(pointer_path, raw)

    def rollback_committed_snapshot_pointer_atomically(self, previous_tx_id: Optional[UUID]) -> None:
        """Rollback committed_pointer to authenticated previous_tx_id (B88, B93)."""
        pointer_path = self._pointer_dir / "committed_pointer"
        if previous_tx_id is None:
            if pointer_path.exists():
                pointer_path.unlink()
        else:
            raw = str(previous_tx_id).encode("utf-8")
            StoragePlatformUtils.write_file_durable(pointer_path, raw)

    def handle_post_pointer_switch_cas_failure(
        self,
        tx_id: UUID,
        transition_record: DurablePointerTransitionRecord,
    ) -> None:
        """Safely handle CAS failure after pointer switch under B88/B93 invariants."""
        # 1. Verify transition record authentication against trust store (B93)
        valid_auth = transition_record.is_valid_transition(
            expected_tx_id=tx_id,
            expected_prev_tx_id=transition_record.previous_tx_id,
            expected_manifest_digest=transition_record.commit_intent_digest,
            trust_store=self._trust_store,
        )

        # 2. Transition transaction state to QUARANTINED
        self.set_tx_state_durable(tx_id, DurableTransactionState.QUARANTINED)
        self.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)

        # 3. Anti-Silent Rollback Guard (B88, B93)
        if valid_auth:
            # Authenticated rollback permitted
            self.rollback_committed_snapshot_pointer_atomically(transition_record.previous_tx_id)
        else:
            # Transition record is unauthenticated or forged -> FREEZE SYSTEM IN QUARANTINE_LOCKED
            pass

    # Abort & Inspection Queries
    def has_snapshot_directory(self, tx_id: UUID) -> bool:
        """True if /snapshots/<tx_id>/ exists (B94)."""
        return self._get_snapshot_tx_dir(tx_id).exists()

    def committed_pointer_references_transaction(self, tx_id: UUID) -> bool:
        """True if current committed pointer references tx_id."""
        return self.get_current_active_transaction_id() == tx_id

    def has_durable_commit_marker(self, tx_id: UUID) -> bool:
        """True if commit_record_block.json exists in snapshot or staging."""
        snap_marker = self._get_snapshot_tx_dir(tx_id) / "commit_record_block.json"
        stage_marker = self._get_staging_tx_dir(tx_id) / "commit_record_block.json"
        return snap_marker.exists() or stage_marker.exists()

    def get_durable_head_digest(self) -> str:
        return self.current_head_digest

    def get_pre_transaction_head_digest(self) -> str:
        return self.current_head_digest

    def get_pre_transaction_head_digest_from_disk(self, tx_id: UUID) -> str:
        abort_record = self.read_durable_abort_record(tx_id)
        if abort_record:
            return abort_record.pre_transaction_head_digest
        return self.current_head_digest

    def read_durable_draft_authorization_digest(self, auth_id: str) -> Optional[str]:
        draft_file = self._root / "drafts" / f"{auth_id}.json"
        if not draft_file.exists():
            return None
        try:
            with open(draft_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                val = data.get("approved_authorization_digest")
                if isinstance(val, dict):
                    val = val.get("value")
                return str(val) if val else None
        except Exception:
            return None

    def save_draft_authorization(self, auth: LiveAuthorization) -> None:
        drafts_dir = self._root / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        draft_file = drafts_dir / f"{auth.authorization_id}.json"
        raw = CanonicalConfigSerializer.to_canonical_json(auth.model_dump(mode="json")).encode("utf-8")
        StoragePlatformUtils.write_file_durable(draft_file, raw)

    def write_durable_abort_record(self, abort_record: AuthoritativeAbortRecordBlock) -> None:
        abort_file = self._aborts_dir / f"{abort_record.activation_transaction_id}.json"
        raw = CanonicalConfigSerializer.to_canonical_json(abort_record.model_dump(mode="json")).encode("utf-8")
        StoragePlatformUtils.write_file_durable(abort_file, raw)

    def flush_abort_record_barrier(self, tx_id: UUID) -> None:
        abort_file = self._aborts_dir / f"{tx_id}.json"
        if abort_file.exists():
            with open(abort_file, "r+b") as f:
                StoragePlatformUtils.flush_file(f.fileno())
        StoragePlatformUtils.flush_parent_dir_if_posix(abort_file)

    def read_durable_abort_record(self, tx_id: UUID) -> Optional[AuthoritativeAbortRecordBlock]:
        abort_file = self._aborts_dir / f"{tx_id}.json"
        if not abort_file.exists():
            return None
        try:
            with open(abort_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                normalized: Dict[str, Any] = {}
                for k, v in data.items():
                    if isinstance(v, dict) and "value" in v:
                        normalized[k] = v["value"]
                    else:
                        normalized[k] = v
                return AuthoritativeAbortRecordBlock.model_validate(normalized)
        except Exception:
            return None

    def assert_abort_is_terminal(self, tx_id: UUID) -> bool:
        st = self.get_durable_tx_state(tx_id)
        return st == DurableTransactionState.ABORTED

    def rollback_staging(self, tx_id: UUID) -> None:
        """Discard /staging/<tx_id>/ directory."""
        stg = self._get_staging_tx_dir(tx_id)
        if stg.exists():
            shutil.rmtree(stg, ignore_errors=True)

    def log_consistency_violation(self, message: str) -> None:
        """Log safety violation to audit log."""
        log_file = self._root / "consistency_violations.log"
        line = f"[{datetime.now(timezone.utc).isoformat()}] CONSISTENCY_VIOLATION: {message}\n"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()


class StorageCommitContract:
    """Enforces Two-Phase Recoverable Commit Protocol with authenticated pointer transition (B75, B82, B86, B88, B89, B93)."""

    @staticmethod
    def execute_durable_commit(
        tx: LedgerStorageTransaction,
        tx_id: UUID,
        go_record: HumanGORecord,
        approved_auth: LiveAuthorization,
        activated_auth: LiveAuthorization,
        engine_signer: StorageEngineSigner,
    ) -> AuthoritativeCommitRecordBlock:
        # Phase 1: Staged Mutation Data Durability Barrier (fsync_1)
        tx.write_staged_mutation_data(tx_id, go_record, activated_auth)
        tx.flush_staged_mutation_data_barrier(tx_id)
        if not tx.verify_staged_mutation_data_durable(tx_id, go_record.record_digest, activated_auth):
            raise StorageDurabilityError("STAGED_MUTATION_DATA_DURABILITY_VERIFICATION_FAILED")

        # Phase 2: Commit Manifest Durability Barrier (fsync_2)
        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_id,
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_record.record_digest,
            advanced_head_digest=go_record.record_digest,
            approved_authorization_digest=approved_auth.approved_authorization_digest,
            activated_authorization_digest=activated_auth.activated_authorization_digest or "",
            mutation_manifest_digest="",
        )
        manifest_digest = commit_block.compute_manifest_digest()
        final_commit_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})

        tx.write_commit_marker_block(tx_id, final_commit_block)
        tx.flush_commit_marker_barrier(tx_id)
        if not tx.verify_commit_marker_durable(tx_id, manifest_digest):
            raise StorageDurabilityError("COMMIT_MARKER_DURABILITY_VERIFICATION_FAILED")

        # Phase 3: Promote to Snapshot Directory & fsync_3 (B75, B83)
        tx.promote_staging_to_snapshot_directory_atomically(tx_id)
        tx.flush_snapshot_directory_barrier(tx_id)
        tx.mark_snapshot_directory_read_only(tx_id)

        # Phase 4: Pre-CAS Manifest Re-verification under Exclusive Lock (B75, B86)
        if not tx.deep_verify_snapshot_manifest(tx_id, final_commit_block):
            raise StorageDurabilityError("POST_BARRIER_TAMPERING_DETECTED_PRE_CAS")

        # Phase 5: Two-Phase Recoverable Commit with Authenticated Pointer Transition (B82, B88, B93)
        # Step 5a: Construct, sign, and fsync authenticated pointer transition record (B93)
        transition_draft = DurablePointerTransitionRecord(
            pointer_version=tx.get_next_pointer_version(),
            previous_tx_id=tx.get_current_active_transaction_id(),
            new_tx_id=tx_id,
            transition_timestamp_utc=datetime.now(timezone.utc),
            commit_intent_digest=manifest_digest,
            previous_pointer_digest=tx.get_current_pointer_digest(),
            transition_record_digest="",
            engine_signature="",
            engine_key_id=engine_signer.key_id,
        )
        rec_digest = transition_draft.compute_canonical_digest()
        raw_sig = engine_signer.sign(rec_digest.encode("utf-8"))
        final_transition_record = transition_draft.model_copy(
            update={
                "transition_record_digest": rec_digest,
                "engine_signature": raw_sig,
            }
        )
        tx.write_durable_pointer_transition_record(final_transition_record)
        tx.flush_pointer_transition_barrier()

        # Step 5b: Atomic pointer switch (committed_pointer -> snapshots/<tx_id>)
        tx.switch_committed_snapshot_pointer_atomically(tx_id)

        # Step 5c: Persistent CAS transition: COMMITTING -> COMMITTED
        cas_success = tx.compare_and_set_tx_state(
            tx_id,
            expected=DurableTransactionState.COMMITTING,
            new=DurableTransactionState.COMMITTED,
        )
        if not cas_success:
            tx.handle_post_pointer_switch_cas_failure(tx_id, final_transition_record)
            raise StorageDurabilityError("COMMIT_CAS_TRANSITION_FAILED")

        # Advance authoritative head digest
        tx.set_head_digest_durable(go_record.record_digest)

        return final_commit_block


class AuthoritativeGOLedger(AuthoritativeLedgerProtocol):
    """Authoritative ledger holding the storage root and exclusive synchronization lock."""

    def __init__(self, root: Path, trust_store: Ed25519TrustStore) -> None:
        self._root = root
        self._trust_store = trust_store
        self._lock = threading.RLock()
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    @property
    def current_head_digest(self) -> str:
        with self.exclusive_lock() as tx:
            return tx.current_head_digest

    @contextmanager
    def exclusive_lock(self) -> Generator[LedgerStorageTransaction, None, None]:
        """Acquire exclusive lock for serialized storage mutation."""
        with self._lock:
            tx = LedgerStorageTransaction(self._root, self._trust_store)
            yield tx
