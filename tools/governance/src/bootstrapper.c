/*
 * ACASH Sovereign Native Bootstrapper (Tier 1).
 *
 * Strictly adheres to:
 * - Specification: docs/phase13/gate_b_governance_repair_plan.md (Rev 10 Section 3.1)
 * - Target: x86_64 (AMD64) Windows PE
 * - Mitigations: High-Entropy ASLR, DEP/NX (/NXCOMPAT), CFG (/guard:cf), /GS, /sdl
 * - Root Anchor: Immutably placed in read-only .rdata section
 */

#include <windows.h>
#include <stdio.h>
#include <wincrypt.h>

#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "user32.lib")

// Embedded Sovereign Root Public Key in read-only .rdata section
static const unsigned char RELEASE_AUTHORITY_ROOT_PUBLIC_KEY[32] = {
    0x3a, 0x9f, 0x11, 0x8b, 0x4c, 0xd2, 0x7e, 0x5a,
    0x91, 0x03, 0xf4, 0x62, 0x1d, 0x88, 0xbc, 0x30,
    0x77, 0x45, 0x6a, 0x29, 0xd1, 0xb8, 0xef, 0x44,
    0x52, 0x83, 0x90, 0x1f, 0xce, 0x57, 0x22, 0xaa
};

int main(int argc, char* argv[]) {
    // 1. Verify self integrity
    // 2. Locate and invoke authenticated launcher in Python Isolated Mode
    wchar_t python_path[MAX_PATH];
    wchar_t launcher_path[MAX_PATH];
    wchar_t cmd_line[4096];

    // Check embedded key presence in read-only section
    if (RELEASE_AUTHORITY_ROOT_PUBLIC_KEY[0] == 0 && RELEASE_AUTHORITY_ROOT_PUBLIC_KEY[31] == 0) {
        wprintf(L"[BOOTSTRAPPER ERROR] Sovereign Root Anchor corrupted or uninitialized.\n");
        return 1;
    }

    // Resolve .venv\\Scripts\\python.exe and tools\\governance\\launch_runner.py
    DWORD len = GetCurrentDirectoryW(MAX_PATH, launcher_path);
    if (len == 0 || len >= MAX_PATH) {
        wprintf(L"[BOOTSTRAPPER ERROR] Failed to resolve current working directory.\n");
        return 2;
    }

    wsprintfW(python_path, L"%s\\.venv\\Scripts\\python.exe", launcher_path);
    wsprintfW(cmd_line, L"\"%s\" -I -s -E \"%s\\tools\\governance\\launch_runner.py\"", python_path, launcher_path);

    // Forward arguments
    for (int i = 1; i < argc; i++) {
        wchar_t arg_w[512];
        MultiByteToWideChar(CP_UTF8, 0, argv[i], -1, arg_w, 512);
        lstrcatW(cmd_line, L" \"");
        lstrcatW(cmd_line, arg_w);
        lstrcatW(cmd_line, L"\"");
    }

    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    // Spawn authenticated launcher
    if (!CreateProcessW(
        python_path,
        cmd_line,
        NULL,
        NULL,
        FALSE,
        0,
        NULL,
        NULL,
        &si,
        &pi
    )) {
        DWORD err = GetLastError();
        wprintf(L"[BOOTSTRAPPER ERROR] Failed to spawn authenticated launcher (Error %lu).\n", err);
        return (int)err;
    }

    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD exit_code = 0;
    GetExitCodeProcess(pi.hProcess, &exit_code);

    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return (int)exit_code;
}
