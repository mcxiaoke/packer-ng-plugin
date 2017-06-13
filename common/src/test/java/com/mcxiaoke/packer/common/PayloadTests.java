package com.mcxiaoke.packer.common;

import com.android.apksig.ApkVerifier;
import com.android.apksig.ApkVerifier.Builder;
import com.android.apksig.ApkVerifier.IssueWithParams;
import com.android.apksig.ApkVerifier.Result;
import com.android.apksig.apk.ApkFormatException;
import com.mcxiaoke.packer.support.walle.Support;
import junit.framework.TestCase;

import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.security.NoSuchAlgorithmException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * User: mcxiaoke
 * Date: 2017/5/17
 * Time: 16:25
 */
public class PayloadTests extends TestCase {

    @Override
    protected void setUp() throws Exception {
        super.setUp();
    }

    @Override
    protected void tearDown() throws Exception {
        super.tearDown();
    }

    synchronized File newTestFile() throws IOException {
        return TestUtils.newTestFile();
    }

    void checkApkVerified(File f) {
        try {
            assertTrue(TestUtils.apkVerified(f));
        } catch (ApkFormatException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        } catch (NoSuchAlgorithmException e) {
            e.printStackTrace();
        }
    }

    public void testFileExists() {
        File file = new File("../tools/test.apk");
        assertTrue(file.exists());
    }

    public void testFileCopy() throws IOException {
        File f1 = new File("../tools/test.apk");
        File f2 = newTestFile();
        assertTrue(f2.exists());
        assertTrue(f2.getName().endsWith(".apk"));
        assertEquals(f1.length(), f2.length());
        assertEquals(f1.getParent(), f2.getParent());
    }

    public void testFileSignature() throws IOException,
            ApkFormatException,
            NoSuchAlgorithmException {
        File f = newTestFile();
        checkApkVerified(f);
    }

    public void testOverrideSignature() throws IOException,
            ApkFormatException,
            NoSuchAlgorithmException {
        File f = newTestFile();
        // don't write with APK Signature Scheme v2 Block ID 0x7109871a
        PackerCommon.writeString(f, "OverrideSignatureSchemeBlock", 0x7109871a);
        assertEquals("OverrideSignatureSchemeBlock", PackerCommon.readString(f, 0x7109871a));
        ApkVerifier verifier = new Builder(f).build();
        Result result = verifier.verify();
        final List<IssueWithParams> errors = result.getErrors();
        if (errors != null && errors.size() > 0) {
            for (IssueWithParams error : errors) {
                System.out.println("testOverrideSignature " + error);
            }
        }
        assertTrue(result.containsErrors());
        assertFalse(result.isVerified());
        assertFalse(result.isVerifiedUsingV1Scheme());
        assertFalse(result.isVerifiedUsingV2Scheme());
    }

    public void testBytesWrite1() throws IOException {
        File f = newTestFile();
        byte[] in = "Hello".getBytes();
        Support.writeBlock(f, 0x12345, in);
        byte[] out = Support.readBytes(f, 0x12345);
        assertTrue(TestUtils.sameBytes(in, out));
        checkApkVerified(f);
    }

    public void testBytesWrite2() throws IOException {
        File f = newTestFile();
        byte[] in = "中文和特殊符号测试！@#¥%……*（）《》？：【】、".getBytes("UTF-8");
        Support.writeBlock(f, 0x12345, in);
        byte[] out = Support.readBytes(f, 0x12345);
        assertTrue(TestUtils.sameBytes(in, out));
        checkApkVerified(f);
    }

    public void testStringWrite() throws IOException {
        File f = newTestFile();
        PackerCommon.writeString(f, "Test String", 0x717a786b);
        assertEquals("Test String", PackerCommon.readString(f, 0x717a786b));
        PackerCommon.writeString(f, "中文和特殊符号测试！@#¥%……*（）《》？：【】、", 0x717a786b);
        assertEquals("中文和特殊符号测试！@#¥%……*（）《》？：【】、", PackerCommon.readString(f, 0x717a786b));
        checkApkVerified(f);
    }

    public void testValuesWrite() throws IOException {
        File f = newTestFile();
        Map<String, String> in = new HashMap<>();
        in.put("Channel", "HelloWorld");
        in.put("名字", "哈哈啊哈哈哈");
        in.put("!@#$!%^@&*()_+\"?:><", "渠道Google");
        in.put("12345abcd", "2017");
        PackerCommon.writeValues(f, in, 0x12345);
        Map<String, String> out = PackerCommon.readValues(f, 0x12345);
        assertNotNull(out);
        assertEquals(in.size(), out.size());
        for (Map.Entry<String, String> entry : in.entrySet()) {
            assertEquals(entry.getValue(), out.get(entry.getKey()));
        }
        checkApkVerified(f);
    }

    public void testValuesMixedWrite() throws IOException {
        File f = newTestFile();
        Map<String, String> in = new HashMap<>();
        in.put("!@#$!%^@&*()_+\"?:><", "渠道Google");
        in.put("12345abcd", "2017");
        PackerCommon.writeValues(f, in, 0x123456);
        PackerCommon.writeValue(f, "hello", "Mixed", 0x8888);
        Map<String, String> out = PackerCommon.readValues(f, 0x123456);
        assertNotNull(out);
        assertEquals(in.size(), out.size());
        for (Map.Entry<String, String> entry : in.entrySet()) {
            assertEquals(entry.getValue(), out.get(entry.getKey()));
        }
        assertEquals("Mixed", PackerCommon.readValue(f, "hello", 0x8888));
        PackerCommon.writeString(f, "RawValue", 0x2017);
        assertEquals("RawValue", PackerCommon.readString(f, 0x2017));
        PackerCommon.writeString(f, "OverrideValues", 0x123456);
        assertEquals("OverrideValues", PackerCommon.readString(f, 0x123456));
        checkApkVerified(f);
    }

    public void testByteBuffer() throws IOException {
        byte[] string = "Hello".getBytes();
        ByteBuffer buf = ByteBuffer.allocate(1024);
        buf.order(ByteOrder.LITTLE_ENDIAN);
        buf.putInt(123);
        buf.putChar('z');
        buf.putShort((short) 2017);
        buf.putFloat(3.1415f);
        buf.put(string);
        buf.putLong(9876543210L);
        buf.putDouble(3.14159265);
        buf.put((byte) 5);
        buf.flip(); // important
//        TestUtils.showBuffer(buf);
        assertEquals(123, buf.getInt());
        assertEquals('z', buf.getChar());
        assertEquals(2017, buf.getShort());
        assertEquals(3.1415f, buf.getFloat());
        byte[] so = new byte[string.length];
        buf.get(so);
        assertTrue(TestUtils.sameBytes(string, so));
        assertEquals(9876543210L, buf.getLong());
        assertEquals(3.14159265, buf.getDouble());
        assertEquals((byte) 5, buf.get());
    }

    public void testBufferWrite() throws IOException {
        File f = newTestFile();
        byte[] string = "Hello".getBytes();
        ByteBuffer in = ByteBuffer.allocate(1024);
        in.order(ByteOrder.LITTLE_ENDIAN);
        in.putInt(123);
        in.putChar('z');
        in.putShort((short) 2017);
        in.putFloat(3.1415f);
        in.putLong(9876543210L);
        in.putDouble(3.14159265);
        in.put((byte) 5);
        in.put(string);
        in.flip(); // important
//        TestUtils.showBuffer(in);
        Support.writeBlock(f, 0x123456, in);
        ByteBuffer out = Support.readBlock(f, 0x123456);
        assertNotNull(out);
//        TestUtils.showBuffer(out);
        assertEquals(123, out.getInt());
        assertEquals('z', out.getChar());
        assertEquals(2017, out.getShort());
        assertEquals(3.1415f, out.getFloat());
        assertEquals(9876543210L, out.getLong());
        assertEquals(3.14159265, out.getDouble());
        assertEquals((byte) 5, out.get());
        byte[] so = new byte[string.length];
        out.get(so);
        assertTrue(TestUtils.sameBytes(string, so));
        checkApkVerified(f);
    }

    public void testChannelWriteRead() throws IOException {
        File f = newTestFile();
        PackerCommon.writeChannel(f, "Hello");
        assertEquals("Hello", PackerCommon.readChannel(f));
        PackerCommon.writeChannel(f, "中文");
        assertEquals("中文", PackerCommon.readChannel(f));
        PackerCommon.writeChannel(f, "中文 C");
        assertEquals("中文 C", PackerCommon.readChannel(f));
        checkApkVerified(f);
    }

}
