"""Exercise the real packer boundary with synthetic, credential-free images."""
import importlib.util
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

tool = Path(__file__).resolve().parents[1] / 'tools/pack-pbboot.py'
spec = importlib.util.spec_from_file_location('packer', tool)
packer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packer)

def inputs():
    payload = b'public synthetic test payload'
    header = bytearray(struct.pack('>7I4B32s', 0x27051956, 0, 0, len(payload),
        0x80001000, 0x80001000, zlib.crc32(payload), 5, 5, 2, 0, b'test'))
    struct.pack_into('>I', header, 4, zlib.crc32(header))
    ubi = bytearray(b'\xff' * packer.PEB)
    ubi[:64] = b'\x00' * 64
    ubi[:5] = b'UBI#\x01'
    struct.pack_into('>II', ubi, 16, 2048, 4096)
    struct.pack_into('>I', ubi, 60, zlib.crc32(ubi[:60]) ^ 0xffffffff)
    return bytes(header) + payload, bytes(ubi)

class FormatTests(unittest.TestCase):
    def test_cli_and_no_overwrite(self):
        kernel, ubi = inputs()
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / 'kernel').write_bytes(kernel)
            (directory / 'ubi').write_bytes(ubi)
            command = [sys.executable, str(tool), '--kernel', str(directory / 'kernel'),
                '--ubi', str(directory / 'ubi'), '--output', str(directory / 'factory')]
            result = subprocess.run(command, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = (directory / 'factory').read_bytes()
            self.assertEqual(data[:len(kernel)], kernel)
            self.assertEqual(data[len(kernel):packer.KERNEL_PARTITION], b'\xff' * (packer.KERNEL_PARTITION-len(kernel)))
            self.assertEqual(data[packer.KERNEL_PARTITION:], ubi)
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual((directory / 'factory').read_bytes(), data)

    def test_corrupt_inputs_rejected(self):
        kernel, ubi = inputs()
        for bad_kernel, bad_ubi in [
            (kernel[:-1], ubi), (kernel[:10] + b'\x01' + kernel[11:], ubi),
            (kernel[:-1] + b'!', ubi), (kernel, ubi[:-1]),
            (kernel, b'FAIL' + ubi[4:]),
            (kernel, ubi[:17] + b'\x01' + ubi[18:]),
            (kernel, ubi[:60] + b'FAIL' + ubi[64:]),
        ]:
            with self.subTest():
                with self.assertRaises(ValueError):
                    packer.validate(bad_kernel, bad_ubi)

if __name__ == '__main__':
    unittest.main()
