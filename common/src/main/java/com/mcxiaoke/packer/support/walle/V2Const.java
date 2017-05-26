package com.mcxiaoke.packer.support.walle;

/**
 * User: mcxiaoke
 * Date: 2017/5/17
 * Time: 15:08
 */
class V2Const {
    // V2 Scheme Constants
    public static final long APK_SIG_BLOCK_MAGIC_HI = 0x3234206b636f6c42L;
    public static final long APK_SIG_BLOCK_MAGIC_LO = 0x20676953204b5041L;
    public static final int APK_SIG_BLOCK_MIN_SIZE = 32;
    /**
     * The v2 signature of the APK is stored as an ID-value pair with ID 0x7109871a
     * (https://source.android.com/security/apksigning/v2.html#apk-signing-block)
     **/
    public static final int APK_SIGNATURE_SCHEME_V2_BLOCK_ID = 0x7109871a;
    public static final int CONTENT_DIGESTED_CHUNK_MAX_SIZE_BYTES = 1024 * 1024;
    /**
     * APK Signing Block Magic Code: magic “APK Sig Block 42” (16 bytes)
     * "APK Sig Block 42" : 41 50 4B 20 53 69 67 20 42 6C 6F 63 6B 20 34 32
     */
    public static final byte[] APK_SIGNING_BLOCK_MAGIC =
            new byte[]{
                    0x41, 0x50, 0x4b, 0x20, 0x53, 0x69, 0x67, 0x20,
                    0x42, 0x6c, 0x6f, 0x63, 0x6b, 0x20, 0x34, 0x32,
            };

    // ZIP Constants
    public static final int ZIP_EOCD_REC_MIN_SIZE = 22;
    public static final int ZIP_EOCD_REC_SIG = 0x06054b50;
    public static final int ZIP_EOCD_CENTRAL_DIR_TOTAL_RECORD_COUNT_OFFSET = 10;
    public static final int ZIP_EOCD_CENTRAL_DIR_SIZE_FIELD_OFFSET = 12;
    public static final int ZIP_EOCD_CENTRAL_DIR_OFFSET_FIELD_OFFSET = 16;
    public static final int ZIP_EOCD_COMMENT_LENGTH_FIELD_OFFSET = 20;
    public static final int ZIP64_EOCD_LOCATOR_SIZE = 20;
    public static final int ZIP64_EOCD_LOCATOR_SIG = 0x07064b50;
    public static final int UINT16_MAX_VALUE = 0xffff;
}
