from django.test import SimpleTestCase

from omogenjudge.submissions.feedback import decode_for_display, signal_name


class DecodeForDisplayTests(SimpleTestCase):

    def testPlainText(self):
        decoded = decode_for_display(b'1 2 3\nhello\tworld\r\n')
        self.assertEqual(decoded.text, '1 2 3\nhello\tworld\r\n')
        self.assertFalse(decoded.truncated)

    def testNone(self):
        decoded = decode_for_display(None)
        self.assertEqual(decoded.text, '')
        self.assertFalse(decoded.truncated)

    def testMemoryview(self):
        # This is what the database driver returns for binary columns.
        self.assertEqual(decode_for_display(memoryview(b'abc')).text, 'abc')

    def testUnicode(self):
        self.assertEqual(decode_for_display('räksmörgås ✓'.encode('utf-8')).text, 'räksmörgås ✓')

    def testInvalidUtf8IsReplaced(self):
        self.assertEqual(decode_for_display(b'a\xffb\xfe').text, 'a�b�')

    def testControlCharactersAreReplaced(self):
        self.assertEqual(decode_for_display(b'a\x00b\x1b[31mc\x7f').text, 'a�b�[31mc�')

    def testMarkupIsKeptAsText(self):
        # Escaping is the job of the template; decoding must not mark anything as safe.
        decoded = decode_for_display(b'<script>alert(1)</script>')
        self.assertEqual(decoded.text, '<script>alert(1)</script>')
        self.assertFalse(hasattr(decoded.text, '__html__'))

    def testTruncatedInTheMiddleOfACharacter(self):
        data = 'aå'.encode('utf-8')
        self.assertEqual(len(data), 3)
        decoded = decode_for_display(data[:2], truncated=True)
        self.assertEqual(decoded.text, 'a')
        self.assertTrue(decoded.truncated)

    def testIncompleteCharacterWithoutTruncation(self):
        data = 'aå'.encode('utf-8')
        self.assertEqual(decode_for_display(data[:2]).text, 'a�')


class SignalNameTests(SimpleTestCase):

    def testKnownSignals(self):
        self.assertEqual(signal_name(11), 'SIGSEGV')
        self.assertEqual(signal_name(9), 'SIGKILL')
        self.assertEqual(signal_name(6), 'SIGABRT')

    def testUnknownSignal(self):
        self.assertIsNone(signal_name(0))
        self.assertIsNone(signal_name(12345))

    def testNoSignal(self):
        self.assertIsNone(signal_name(None))
