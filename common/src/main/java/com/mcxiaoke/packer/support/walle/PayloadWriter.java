package com.mcxiaoke.packer.support.walle;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;


final class PayloadWriter {
    private PayloadWriter() {
        super();
    }

    public static void writeBlock(File apkFile, final int id,
                                  final byte[] bytes) throws IOException {
        final ByteBuffer byteBuffer = ByteBuffer.allocate(bytes.length);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN);
        byteBuffer.put(bytes, 0, bytes.length);
        byteBuffer.flip();
        writeBlock(apkFile, id, byteBuffer);
    }

    public static void writeBlock(final File apkFile, final int id,
                                  final ByteBuffer buffer) throws IOException {
        final Map<Integer, ByteBuffer> idValues = new HashMap<>();
        idValues.put(id, buffer);
        writeValues(apkFile, idValues);
    }

    /**
     * writeBlock new idValues into apk, update if id exists
     * NOTE: use unknown IDs. DO NOT use ID that have already been used.  See <a href='https://source.android.com/security/apksigning/v2.html'>APK Signature Scheme v2</a>
     */
    private static void writeValues(final File apkFile, final Map<Integer, ByteBuffer> idValues) throws IOException {
        final ApkSigningBlockHandler handler = new ApkSigningBlockHandler() {
            @Override
            public ApkSigningBlock handle(final Map<Integer, ByteBuffer> originIdValues) {
                if (idValues != null && !idValues.isEmpty()) {
                    originIdValues.putAll(idValues);
                }
                final ApkSigningBlock apkSigningBlock = new ApkSigningBlock();
                final Set<Map.Entry<Integer, ByteBuffer>> entrySet = originIdValues.entrySet();
                for (Map.Entry<Integer, ByteBuffer> entry : entrySet) {
                    final ApkSigningPayload payload = new ApkSigningPayload(entry.getKey(), entry.getValue());
                    apkSigningBlock.addPayload(payload);
                }
                return apkSigningBlock;
            }
        };
        writeApkSigningBlock(apkFile, handler);
    }

    static void writeApkSigningBlock(final File apkFile, final ApkSigningBlockHandler handler) throws IOException {
        RandomAccessFile raf = null;
        FileChannel fc = null;
        try {
            raf = new RandomAccessFile(apkFile, "rw");
            fc = raf.getChannel();
            final long commentLength = ApkUtil.findZipCommentLength(fc);
            final long centralDirStartOffset = ApkUtil.findCentralDirStartOffset(fc, commentLength);
            // Find the APK Signing Block. The block immediately precedes the Central Directory.
            final Pair<ByteBuffer, Long> apkSigningBlockAndOffset = ApkUtil.findApkSigningBlock(fc, centralDirStartOffset);
            final ByteBuffer apkSigningBlock2 = apkSigningBlockAndOffset.getFirst();
            final long apkSigningBlockOffset = apkSigningBlockAndOffset.getSecond();

            if (centralDirStartOffset == 0 || apkSigningBlockOffset == 0) {
                throw new IOException(
                        "No APK Signature Scheme v2 block in APK Signing Block");
            }
            final Map<Integer, ByteBuffer> originIdValues = ApkUtil.findIdValues(apkSigningBlock2);
            // Find the APK Signature Scheme v2 Block inside the APK Signing Block.
            final ByteBuffer apkSignatureSchemeV2Block = originIdValues.get(V2Const.APK_SIGNATURE_SCHEME_V2_BLOCK_ID);

            if (apkSignatureSchemeV2Block == null) {
                throw new IOException(
                        "No APK Signature Scheme v2 block in APK Signing Block");
            }
            final ApkSigningBlock apkSigningBlock = handler.handle(originIdValues);
            // read CentralDir
            raf.seek(centralDirStartOffset);
            final byte[] centralDirBytes = new byte[(int) (fc.size() - centralDirStartOffset)];
            raf.read(centralDirBytes);

            fc.position(apkSigningBlockOffset);

            final long length = apkSigningBlock.writeTo(raf);

            // store CentralDir
            raf.write(centralDirBytes);
            // update length
            raf.setLength(raf.getFilePointer());

            // update CentralDir Offset
            // End of central directory record (EOCD)
            // Offset     Bytes     Description[23]
            // 0            4       End of central directory signature = 0x06054b50
            // 4            2       Number of this disk
            // 6            2       Disk where central directory starts
            // 8            2       Number of central directory records on this disk
            // 10           2       Total number of central directory records
            // 12           4       Size of central directory (bytes)
            // 16           4       Offset of start of central directory, relative to start of archive
            // 20           2       Comment length (n)
            // 22           n       Comment

            raf.seek(fc.size() - commentLength - 6);
            // 6 = 2(Comment length) + 4
            // (Offset of start of central directory, relative to start of archive)
            final ByteBuffer temp = ByteBuffer.allocate(4);
            temp.order(ByteOrder.LITTLE_ENDIAN);
            temp.putInt((int) (centralDirStartOffset + length + 8 - (centralDirStartOffset - apkSigningBlockOffset)));
            // 8 = size of block in bytes (excluding this field) (uint64)
            temp.flip();
            raf.write(temp.array());

        } finally {
            V2Utils.close(fc);
            V2Utils.close(raf);
        }
    }

    interface ApkSigningBlockHandler {
        ApkSigningBlock handle(Map<Integer, ByteBuffer> originIdValues);
    }
}
