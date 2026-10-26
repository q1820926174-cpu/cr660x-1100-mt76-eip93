"""Pack an independently built uImage and UBI. Never connects to a device."""
import argparse
import hashlib
from pathlib import Path
import struct
import zlib

KERNEL_PARTITION = 0x400000
FIRMWARE_LIMIT = 0x7D80000
PEB = 0x20000

def validate(kernel, ubi):
    if not 64 < len(kernel) <= KERNEL_PARTITION:
        raise ValueError('uImage length outside kernel partition')
    header = bytearray(kernel[:64])
    magic, header_crc, _, size, load, entry, data_crc = struct.unpack_from('>7I', header)
    struct.pack_into('>I', header, 4, 0)
    if magic != 0x27051956 or zlib.crc32(header) & 0xffffffff != header_crc:
        raise ValueError('uImage header CRC or magic invalid')
    if size != len(kernel) - 64 or zlib.crc32(kernel[64:]) & 0xffffffff != data_crc:
        raise ValueError('uImage data length or CRC invalid')
    if (load, entry) != (0x80001000, 0x80001000):
        raise ValueError('Unexpected CR660x kernel entry/load address')
    if tuple(kernel[28:32]) != (5, 5, 2, 0):
        raise ValueError('Expected Linux/MIPS/kernel/uncompressed-loader uImage')
    if not ubi or len(ubi) % PEB or KERNEL_PARTITION + len(ubi) > FIRMWARE_LIMIT:
        raise ValueError('UBI length/alignment outside firmware partition')
    for offset in range(0, len(ubi), PEB):
        ec = ubi[offset:offset + 64]
        if ec[:5] != b'UBI#\x01' or struct.unpack_from('>II', ec, 16) != (2048, 4096):
            raise ValueError('Expected UBI v1, VID offset 2048, data offset 4096')
        # UBI stores an uncomplemented CRC initialized with 0xffffffff.
        crc = (zlib.crc32(ec[:60]) ^ 0xffffffff) & 0xffffffff
        if crc != struct.unpack_from('>I', ec, 60)[0]:
            raise ValueError('Invalid UBI EC header CRC')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel', type=Path, required=True)
    parser.add_argument('--ubi', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    kernel, ubi = args.kernel.read_bytes(), args.ubi.read_bytes()
    validate(kernel, ubi)
    image = kernel + b'\xff' * (KERNEL_PARTITION - len(kernel)) + ubi
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as target:
        target.write(image)
    digest = hashlib.sha256(image).hexdigest()
    args.output.with_suffix(args.output.suffix + '.sha256').write_text(digest + '  ' + args.output.name + '\n')
    print(f'{args.output.name}: {len(image)} bytes; SHA256 {digest}')

if __name__ == '__main__':
    main()
