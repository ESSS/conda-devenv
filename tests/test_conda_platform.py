import platform
import sys

from conda_devenv.devenv import CondaPlatform


def test_current_platform_linux32(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(platform, "machine", lambda: "i386")
    monkeypatch.setattr(platform, "architecture", lambda: ["32bit", "ELF"])
    assert CondaPlatform.current() == CondaPlatform.Linux32


def test_current_platform_linux64(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(platform, "architecture", lambda: ["64bit", "ELF"])
    assert CondaPlatform.current() == CondaPlatform.Linux64


def test_current_platform_linux_aarch64(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(platform, "machine", lambda: "aarch64")
    monkeypatch.setattr(platform, "architecture", lambda: ["64bit", "ELF"])
    assert CondaPlatform.current() == CondaPlatform.LinuxAArch64


def test_current_platform_win32(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(platform, "machine", lambda: "x86")
    monkeypatch.setattr(platform, "architecture", lambda: ["32bit", "WindowsPE"])
    assert CondaPlatform.current() == CondaPlatform.Win32


def test_current_platform_win64(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(platform, "architecture", lambda: ["64bit", "WindowsPE"])
    assert CondaPlatform.current() == CondaPlatform.Win64


def test_current_platform_win_arm64(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(platform, "machine", lambda: "ARM64")
    monkeypatch.setattr(platform, "architecture", lambda: ["64bit", "WindowsPE"])
    assert CondaPlatform.current() == CondaPlatform.WinArm64


def test_current_platform_osx32(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(platform, "machine", lambda: "x86")
    monkeypatch.setattr(platform, "architecture", lambda: ["32bit", ""])
    assert CondaPlatform.current() == CondaPlatform.Osx32


def test_current_platform_osx64(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(platform, "architecture", lambda: ["64bit", ""])
    assert CondaPlatform.current() == CondaPlatform.Osx64


def test_current_platform_osx_arm64(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    monkeypatch.setattr(platform, "architecture", lambda: ["64bit", ""])
    assert CondaPlatform.current() == CondaPlatform.OsxArm64
