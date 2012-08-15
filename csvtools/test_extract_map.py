import unittest
import mock
from mock import sentinel
from csvtools.test import ReaderWriter
import csvtools.extract_map as m


def mmap():
    # mocked out Map - will not write to fs
    map = m.Map('', 'id')
    map.write = mock.Mock()
    return map


class Test_Map_field_names(unittest.TestCase):

    def test(self):
        map = m.Map('a,b', 'id')

        self.assertEqual(set(('a', 'b', 'id')), set(map.field_names))


class Test_Map_bind(unittest.TestCase):

    def test_binds_the_internal_transformer(self):
        map = m.Map('a,b', 'id')

        map.bind(('a', 'b', 'c'))

        self.assertEqual(('a', 'b'), map.transformer.transform(('a', 'b', 'c')))


class Test_Map_translate(unittest.TestCase):

    def test_uses_internal_transformer(self):
        map = m.Map('aa,bb', 'id')
        map.transformer = mock.Mock()
        map.transformer.transform = mock.Mock(return_value=(sentinel.aa1, sentinel.bb1))

        map.values = {
            (sentinel.aa1, sentinel.bb1): sentinel.ref1,
        }

        input_row = ('prefix', sentinel.bb1, 'middle', sentinel.aa1, 'suffix')
        ref = map.translate(input_row)

        map.transformer.transform.assert_called_once_with(input_row)
        self.assertEqual(sentinel.ref1, ref)

    def fixture_aa_bb_with_aa1_bb1_1(self):
        map = m.Map('aa,bb', 'id')
        map.bind(('aa', 'bb'))

        map.values = {
            (sentinel.aa1, sentinel.bb1): 1,
        }
        map.next_ref = 2

        return map

    def test_if_not_in_values_adds_new_value(self):
        map = self.fixture_aa_bb_with_aa1_bb1_1()

        ref = map.translate((sentinel.aa_notin, sentinel.bb_notin))

        self.assertEqual(
            {
                (sentinel.aa1, sentinel.bb1): 1,
                (sentinel.aa_notin, sentinel.bb_notin): 2
            },
            map.values)

    def test_if_not_in_values_ref_returned_is_previous_next_ref(self):
        map = self.fixture_aa_bb_with_aa1_bb1_1()
        map.modified = False

        previous_next_ref = map.next_ref
        ref = map.translate((sentinel.aa_notin, sentinel.bb_notin))

        self.assertEqual(previous_next_ref, ref)

    def test_if_not_in_values_next_ref_is_incremented(self):
        map = self.fixture_aa_bb_with_aa1_bb1_1()
        map.modified = False

        previous_next_ref = map.next_ref
        ref = map.translate((sentinel.aa_notin, sentinel.bb_notin))

        self.assertEqual(previous_next_ref + 1, map.next_ref)

    def test_if_not_in_values_sets_modified(self):
        map = self.fixture_aa_bb_with_aa1_bb1_1()
        map.modified = False

        map.translate((sentinel.aa_notin, sentinel.bb_notin))

        self.assertTrue(map.modified)

    def test_if_modified_and_in_values_remains_modified(self):
        map = self.fixture_aa_bb_with_aa1_bb1_1()
        map.modified = True

        map.translate((sentinel.aa1, sentinel.bb1))

        self.assertTrue(map.modified)

    def test_if_unmodified_and_in_values_remains_unmodified(self):
        map = self.fixture_aa_bb_with_aa1_bb1_1()
        map.modified = False

        map.translate((sentinel.aa1, sentinel.bb1))

        self.assertFalse(map.modified)

    def test_empty_map(self):
        map = m.Map('aa', 'id')
        map.bind(['aa'])

        map.translate([sentinel.new])

        self.assertEqual({(sentinel.new,): 0}, map.values)


class Test_Map_write(unittest.TestCase):

    def test_header(self):
        map = m.Map('aa,bb', 'id')

        writer = ReaderWriter()
        map.write(writer)

        self.assertEqual([('id', 'aa', 'bb')], writer.rows)

    def test_content(self):
        map = m.Map('aa,bb', 'id')
        map.values = {
            (sentinel.aa1, sentinel.bb1): sentinel.ref1,
            (sentinel.aa2, sentinel.bb2): sentinel.ref2
        }

        writer = ReaderWriter()
        map.write(writer)

        self.assertEqual(
            sorted([(sentinel.ref1, sentinel.aa1, sentinel.bb1),
            (sentinel.ref2, sentinel.aa2, sentinel.bb2)]), sorted(writer.rows[1:]))


class Test_Map_read(unittest.TestCase):

    header = ('id', 'aa', 'bb')

    def write_aa1_aa2_88(self, writer):
        map = m.Map('aa,bb', 'id')
        map.values = {
            (sentinel.aa1, sentinel.bb1): 88,
            (sentinel.aa2, sentinel.bb2): 19
        }
        map.write(writer)

    def test_values_read_back(self):
        rw = ReaderWriter()
        self.write_aa1_aa2_88(rw)

        newmap = m.Map('aa,bb', 'id')
        newmap.read(rw)

        self.assertEqual(
            {
            (sentinel.aa1, sentinel.bb1): 88,
            (sentinel.aa2, sentinel.bb2): 19
            },
            newmap.values)

    def test_next_ref_is_set_to_maxref_plus_1(self):
        rw = ReaderWriter()
        self.write_aa1_aa2_88(rw)

        newmap = m.Map('aa,bb', 'id')
        newmap.read(rw)

        self.assertEqual(89, newmap.next_ref)

    def test_fields_swapped_properly_reads_back(self):
        rw = ReaderWriter()
        self.write_aa1_aa2_88(rw)

        newmap = m.Map('bb,aa', 'id')
        newmap.read(rw)

        self.assertEqual(
            {
            (sentinel.bb1, sentinel.aa1): 88,
            (sentinel.bb2, sentinel.aa2): 19
            },
            newmap.values)

    def test_refs_not_unique_dies(self):
        reader = ReaderWriter()
        reader.rows = [self.header, (1, 1, 1), (1, 2, 2)]
        map = m.Map('aa,bb', 'id')

        self.assertRaises(Exception, lambda: map.read(reader))

    def test_valuess_not_unique_dies(self):
        reader = ReaderWriter()
        reader.rows = [self.header, (1, 1, 1), (2, 1, 1)]
        map = m.Map('aa,bb', 'id')

        self.assertRaises(Exception, lambda: map.read(reader))

    def test_missing_ref_field(self):
        reader = ReaderWriter()
        reader.rows = [('aa', 'bb')]
        map = m.Map('aa,bb', 'id')

        self.assertRaises(Exception, lambda: map.read(reader))

    def test_missing_value_field(self):
        reader = ReaderWriter()
        reader.rows = [('id', 'bb')]
        map = m.Map('aa,bb', 'id')

        self.assertRaises(Exception, lambda: map.read(reader))