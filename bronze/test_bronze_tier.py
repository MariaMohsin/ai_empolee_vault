#!/usr/bin/env python3
"""
Bronze Tier Automated Test Suite
Tests all core functionality of the Bronze Tier AI Employee system.
"""

import time
import shutil
from pathlib import Path
from datetime import datetime

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(message):
    print(f"{Colors.BLUE}[TEST]{Colors.END} {message}")

def print_pass(message):
    print(f"{Colors.GREEN}[PASS]{Colors.END} {message}")

def print_fail(message):
    print(f"{Colors.RED}[FAIL]{Colors.END} {message}")

def print_info(message):
    print(f"{Colors.YELLOW}[INFO]{Colors.END} {message}")

# Setup paths
VAULT = Path(__file__).parent
INBOX = VAULT / "Inbox"
NEEDS = VAULT / "Needs_Action"
DONE = VAULT / "Done"
ARCHIVE = VAULT / "Inbox_Archive"
LOGS = VAULT / "Logs"

def test_folder_structure():
    """Test 1: Verify all required folders exist"""
    print_test("Testing folder structure...")

    required_folders = [INBOX, NEEDS, DONE, ARCHIVE, LOGS]
    all_exist = True

    for folder in required_folders:
        if folder.exists():
            print_pass(f"  {folder.name}/ exists")
        else:
            print_fail(f"  {folder.name}/ missing")
            all_exist = False

    return all_exist

def test_vault_files():
    """Test 2: Verify required vault files exist"""
    print_test("Testing vault files...")

    required_files = [
        VAULT / "Dashboard.md",
        VAULT / "Company_Handbook.md",
        VAULT / "file_watcher.py"
    ]

    all_exist = True
    for file in required_files:
        if file.exists():
            print_pass(f"  {file.name} exists")
        else:
            print_fail(f"  {file.name} missing")
            all_exist = False

    return all_exist

def test_skills():
    """Test 3: Verify skills exist"""
    print_test("Testing skills...")

    skills_dir = VAULT / "Skills"
    if not skills_dir.exists():
        print_fail("  Skills directory missing")
        return False

    skills = list(skills_dir.glob("*.skill.md"))
    if len(skills) >= 2:
        print_pass(f"  Found {len(skills)} skills:")
        for skill in skills:
            print_pass(f"    - {skill.name}")
        return True
    else:
        print_fail(f"  Only found {len(skills)} skills (need at least 2)")
        return False

def test_file_detection():
    """Test 4: Test file detection workflow (manual mode)"""
    print_test("Testing file detection workflow...")
    print_info("  This test requires manual verification:")
    print_info("  1. Start file_watcher.py in another terminal")
    print_info("  2. This script will create a test file")
    print_info("  3. Watch the watcher terminal for detection")

    response = input("\n  Start watcher in another terminal, then press Enter to continue... ")

    # Create test file
    test_filename = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    test_file = INBOX / test_filename

    test_content = """# Automated Test Task

This is an automated test file created by the Bronze Tier test suite.

**Test timestamp:** {}

**Purpose:** Verify that the file watcher detects new files and creates structured tasks.

## Expected Behavior
- This file should be moved to Inbox_Archive
- A task file should be created in Needs_Action
- The task should have YAML frontmatter

## Test Instructions
If you're reading this as a Claude AI assistant, please:
1. Acknowledge this test
2. Verify the task structure is correct
3. Write a brief response confirming the test passed
4. Move this task to Done when complete

---
**Test ID:** {}
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), test_filename)

    print_info(f"  Creating test file: {test_filename}")
    test_file.write_text(test_content, encoding='utf-8')
    print_pass(f"  Test file created in Inbox")

    # Wait for detection
    print_info("  Waiting 3 seconds for watcher to process...")
    time.sleep(3)

    # Check results
    print_test("Verifying results...")

    results = {
        "Original moved": not test_file.exists(),
        "Archived": (ARCHIVE / test_filename).exists(),
        "Task created": (NEEDS / f"task_{test_filename}").exists()
    }

    all_passed = True
    for check, passed in results.items():
        if passed:
            print_pass(f"  {check}")
        else:
            print_fail(f"  {check}")
            all_passed = False

    if not all_passed:
        print_info("\n  If checks failed, ensure the watcher is running!")
        print_info("  You can manually verify by checking:")
        print_info(f"    - Inbox should be empty")
        print_info(f"    - Inbox_Archive should contain {test_filename}")
        print_info(f"    - Needs_Action should contain task_{test_filename}")

    return all_passed

def cleanup_test_files():
    """Cleanup: Remove test files"""
    print_test("Cleaning up test files...")

    # Find test files
    test_files = []
    test_files.extend(ARCHIVE.glob("test_*.md"))
    test_files.extend(NEEDS.glob("task_test_*.md"))

    if test_files:
        response = input(f"\n  Found {len(test_files)} test files. Delete them? (y/n): ")
        if response.lower() == 'y':
            for f in test_files:
                f.unlink()
                print_pass(f"  Deleted {f.name}")
        else:
            print_info("  Keeping test files")
    else:
        print_info("  No test files to clean up")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  BRONZE TIER AUTOMATED TEST SUITE")
    print("="*60 + "\n")

    tests = [
        ("Folder Structure", test_folder_structure),
        ("Vault Files", test_vault_files),
        ("Skills", test_skills),
        ("File Detection", test_file_detection),
    ]

    results = {}
    for name, test_func in tests:
        print()
        results[name] = test_func()
        print()

    # Summary
    print("="*60)
    print("  TEST SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {name}: {status}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print(f"\n{Colors.GREEN}  ✓ BRONZE TIER: ALL TESTS PASSED!{Colors.END}")
        print(f"{Colors.GREEN}  You're ready to move to Silver Tier! 🥈{Colors.END}\n")
    else:
        print(f"\n{Colors.RED}  ✗ Some tests failed. Review the output above.{Colors.END}\n")

    # Optional cleanup
    print()
    cleanup_test_files()

    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
