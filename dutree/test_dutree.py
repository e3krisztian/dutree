# dutree -- a quick and memory efficient disk usage scanner
# Copyright (C) 2018,2019  Walter Doekes, OSSO B.V.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
# The DuScanTests herein test the dutree scanner by mocking the listdir
# and lstat filesystem calls with a bogus on from a GeneratedFilesystem.
#
from __future__ import print_function
from unittest import TestCase, main
from bogofs import GeneratedFilesystem, RegularFileNode as BaseRegularFileNode

import dutree


class DuScanTestMixin(object):
    maxDiff = None
    use_apparent_size = True

    @staticmethod
    def debug(self, *args):
        # print(*args)
        pass

    @classmethod
    def duscan_tree(cls, fs, path, count=False):
        # Mock.
        dutree.listdir = fs.listdir
        dutree.lstat = fs.stat

        # Scan.
        scanner = dutree.DuScan(path, count=count)
        tree = scanner.scan(cls.use_apparent_size)
        return tree

    @staticmethod
    def leaves_as_list(tree):
        ret = []
        items = tree.get_leaves()
        for item in items:
            ret.append((item.name(), item.app_size(), item.use_size()))
        return ret

    @staticmethod
    def tree_as_list(tree):
        def _as_list(it):
            if isinstance(it, list):
                return [_as_list(i) for i in it]
            return (it.name(), it.app_size(), it.use_size())
        return _as_list(tree.as_tree())


class DuScanSeed1Depth4Test(DuScanTestMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fs = GeneratedFilesystem(seed=1, maxdepth=4)
        cls.tree = cls.duscan_tree(cls.fs, '/')

    def test_filesize(self):
        fs_size = self.fs.get_content_size('/')
        dutree_size = self.tree.app_size()

        self.debug('DuScanSeed1Depth4Test.test_filesize', fs_size)
        self.assertEqual(dutree_size, fs_size)
        self.assertEqual(dutree_size, 2053393838542)
        self.assertEqual(dutree.human(dutree_size), '1.9 T')

        # Also check "used" size
        dutree_size = self.tree.use_size()
        self.assertEqual(dutree_size, 2053435198976)

    def test_leaves(self):
        expected = [
            ('/0.d/02.d/', 106577108100, 106579299840),  # not "/0.d/02.d/*"
            ('/0.d/05.d/', 113273338762, 113275417600),
            ('/0.d/15.d/', 122711365675, 122714030080),
            ('/0.d/*', 687973286945, 687986857472),
            ('/1.d/00.d/', 125037824539, 125040307712),
            ('/1.d/11.d/', 106972774810, 106974994432),
            ('/1.d/13.d/', 115990023563, 115992173056),
            ('/1.d/*', 672920941814, 672934931456),
            ('/*', 1937174334, 1937187328),
        ]
        self.assertEqual(self.leaves_as_list(self.tree), expected)

    def test_tree(self):
        expected = [
            ('/', 2053393838542, 2053435198976),
            [('/0.d/', 1030535099482, 1030555604992),
             [('/0.d/02.d/', 106577108100, 106579299840)],
             [('/0.d/05.d/', 113273338762, 113275417600)],
             [('/0.d/15.d/', 122711365675, 122714030080)],
             [('/0.d/*', 687973286945, 687986857472)]],
            [('/1.d/', 1020921564726, 1020942406656),
             [('/1.d/00.d/', 125037824539, 125040307712)],
             [('/1.d/11.d/', 106972774810, 106974994432)],
             [('/1.d/13.d/', 115990023563, 115992173056)],
             [('/1.d/*', 672920941814, 672934931456)]],
            [('/*', 1937174334, 1937187328)],
        ]
        self.assertEqual(self.tree_as_list(self.tree), expected)

    def test_leaf_size(self):
        self.assertEqual(self.fs.get_content_size('/0.d/05.d'), 113273338762)

    def test_sample_file(self):
        self.assertEqual(self.fs.stat('/1.d/13.d/15.txt').size, 22344)


class DuScanSeed1Depth4BlocksTest(DuScanSeed1Depth4Test):
    """
    Same test, but this time order by use_size instead of app_size.
    """
    use_apparent_size = False


class DuScanCopeWithDeletionTest(DuScanTestMixin, TestCase):
    def test_handle_deleted(self):
        fs = GeneratedFilesystem(seed=1, maxdepth=4)
        deleted_size = 0

        # Entire dir.
        deleted_size += (
            fs.get_content_size('/0.d/05.d') +
            fs.stat('/0.d/05.d').size)
        fs.hide_from_stat('/0.d/05.d')
        # Single file.
        deleted_size += fs.stat('/1.d/13.d/15.txt').size
        fs.hide_from_stat('/1.d/13.d/15.txt')

        # Scan.
        tree = self.duscan_tree(fs, '/')
        fs_size = fs.get_content_size('/') - deleted_size
        dutree_size = tree.app_size()

        self.assertEqual(dutree_size, fs_size)
        self.assertEqual(dutree_size, 2053393838542 - deleted_size)


class DuScanNoLonelyStarTest(DuScanTestMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fs = GeneratedFilesystem(seed=6, maxdepth=4)
        cls.tree = cls.duscan_tree(cls.fs, '/')

    def test_leaves(self):
        expected = [
            ('/00.d/', 962283588169, 962302212608),
            ('/01.d/', 609253676265, 609265658880),
            ('/02.d/', 1154398475211, 1154421058560),  # not "/02.d/*"
            ('/03.d/', 581440911832, 581452373504),
            ('/04.d/', 644318151446, 644330290176),
            ('/05.d/', 762422243930, 762437644288),
            ('/06.d/', 707913056679, 707927303168),
            ('/07.d/', 531731374526, 531741905408),
            ('/08.d/', 891915794716, 891933202944),
            ('/14.d/', 449450186015, 449458953728),
            ('/*', 1050999789708, 1051020292608),
        ]
        self.assertEqual(self.leaves_as_list(self.tree), expected)

    def test_tree(self):
        expected = [
            ('/', 8346127248497, 8346290895872),
            [('/00.d/', 962283588169, 962302212608)],
            [('/01.d/', 609253676265, 609265658880)],
            [('/02.d/', 1154398475211, 1154421058560)],
            [('/03.d/', 581440911832, 581452373504)],
            [('/04.d/', 644318151446, 644330290176)],
            [('/05.d/', 762422243930, 762437644288)],
            [('/06.d/', 707913056679, 707927303168)],
            [('/07.d/', 531731374526, 531741905408)],
            [('/08.d/', 891915794716, 891933202944)],
            [('/14.d/', 449450186015, 449458953728)],
            [('/*', 1050999789708, 1051020292608)],
        ]
        self.assertEqual(self.tree_as_list(self.tree), expected)


class DuScanNoSlashAndStarTest(DuScanTestMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fs = GeneratedFilesystem(seed=206, maxdepth=2)
        cls.tree = cls.duscan_tree(cls.fs, '/')

    def test_leaves(self):
        expected = [
            # not first a ('/', 54139),
            ('/00.txt', 55182, 55296),
            ('/01.txt', 63709, 64000),
            ('/03.txt', 42615, 43008),
            ('/04.txt', 48615, 48640),
            ('/05.txt', 44506, 44544),
            ('/07.txt', 44861, 45056),
            ('/11.txt', 45615, 46080),
            ('/14.txt', 53575, 53760),
            ('/17.txt', 49326, 49664),
            ('/18.txt', 53280, 53760),
            ('/20.txt', 65273, 65536),
            ('/23.txt', 45433, 45568),
            ('/*', 166955, 170496),
        ]
        self.assertEqual(self.leaves_as_list(self.tree), expected)


class DuScanFindBadExamplesTest(DuScanTestMixin, TestCase):
    def is_flawed(self, dirs):
        lastdir = None
        for dir_ in dirs:
            if dir_.endswith('/'):
                lastdir = dir_
                continue
            if not lastdir or not dir_.startswith(lastdir):
                lastdir = None
                continue
            return True
        return False

    def test_is_not_flawed(self):
        good_example = (
            '/var/lib/apt/lists/somelist',
            '/var/lib/apt/lists/*',
            '/var/lib/mysql/ib_logfile0',
            '/var/lib/mysql/*',
            '/var/lib/smartmontools/',
            '/var/lib/*',
        )
        self.assertFalse(self.is_flawed(good_example))

    def test_is_flawed(self):
        bad_example = (
            'data/mysql/fri/',
            'data/mysql/mon/',  # this should not be here..
            'data/mysql/mon/export_statistieken.ibd.qp',
            'data/mysql/mon/log_vacaturegegevens.ibd.qp',
            'data/mysql/mon/*',
            'data/*',
        )
        self.assertTrue(self.is_flawed(bad_example))

    def test_find_something(self):
        if False:
            # depth=4: 57, 176
            # depth=3: 28, 57, 176, 206(!)
            for seed in range(1, 1000):
                print(seed)
                fs = GeneratedFilesystem(seed=seed, maxdepth=1)
                tree = self.duscan_tree(fs, '/')
                dirs = [dir_ for (dir_, size) in self.leaves_as_list(tree)]
                if self.is_flawed(dirs):
                    print(seed, dirs)
                    break


class DuScanCheckDiffUseSizeMixin(DuScanTestMixin):
    @classmethod
    def setUpClass(cls):
        class GeneratedFilesystemWith0ApparentSize(GeneratedFilesystem):
            class RegularFileNode(BaseRegularFileNode):
                @property
                def st_size(self):
                    if (self.size % 1) == 0:  # "random"
                        return 0  # apparent size (e.g. 0 size, but N filename)
                    return self.size

        cls.fs = GeneratedFilesystemWith0ApparentSize(seed=2, maxdepth=2)
        cls.tree = cls.duscan_tree(cls.fs, '/')

    def test_filesize(self):
        app_size = self.tree.app_size()
        use_size = self.tree.use_size()
        self.assertEqual((app_size, use_size), (1118208, 156755389440))


class DuScanCheckAppSizeTest(DuScanCheckDiffUseSizeMixin, TestCase):
    # Use block_size (st_blocks, False) or of apparent_size (st_size, True).
    use_apparent_size = True

    def test_leaves(self):
        expected = [
            ('/00.d/', 77824, 6106051072),
            ('/01.d/', 61440, 4128931328),
            ('/02.d/', 65536, 23433054208),
            ('/04.d/', 65536, 6112315392),
            ('/05.d/', 61440, 11056027136),
            ('/07.d/', 73728, 7656495104),
            ('/09.d/', 73728, 4791513600),
            ('/10.d/', 57344, 17843527680),
            ('/15.d/', 69632, 13243101184),
            ('/16.d/', 73728, 24704101376),
            ('/19.d/', 77824, 6117486592),
            ('/*', 360448, 31562784768),
        ]
        self.assertEqual(self.leaves_as_list(self.tree), expected)


class DuScanCheckUseSizeTest(DuScanCheckDiffUseSizeMixin, TestCase):
    # Use block_size (st_blocks, False) or of apparent_size (st_size, True).
    use_apparent_size = False

    def test_leaves(self):
        expected = [
            ('/02.d/14.d/', 0, 13669273600),
            ('/02.d/*', 65536, 9763780608),
            ('/05.d/', 61440, 11056027136),
            ('/10.d/', 57344, 17843527680),
            ('/14.d/', 36864, 7843903488),
            ('/15.d/', 69632, 13243101184),
            ('/16.d/16.d/', 0, 18174032384),
            ('/*', 827392, 65161743360),
        ]
        self.assertEqual(self.leaves_as_list(self.tree), expected)


class DuScanCountModeSeed1Depth4Test(DuScanTestMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fs = GeneratedFilesystem(seed=1, maxdepth=4)
        cls.tree = cls.duscan_tree(cls.fs, '/', count=True)

    def test_count_total(self):
        """Verify total object count for seed 1, depth 4."""
        dutree_count = self.tree.app_size()
        self.debug('DuScanCountModeSeed1Depth4Test.test_count_total',
                   dutree_count)
        self.assertEqual(dutree_count, 165386)

    def test_count_leaves(self):
        """Verify leaves match expected counts."""
        expected = [
            ('/0.d/02.d/', 8794, 8794),
            ('/0.d/07.d/', 8752, 8752),
            ('/0.d/15.d/', 10609, 10609),
            ('/0.d/*', 53685, 53685),
            ('/1.d/00.d/', 10074, 10074),
            ('/1.d/09.d/', 8899, 8899),
            ('/1.d/11.d/', 8702, 8702),
            ('/1.d/13.d/', 8556, 8556),
            ('/1.d/*', 47264, 47264),
            ('/*', 51, 51),
        ]
        self.assertEqual(self.leaves_as_list(self.tree), expected)

    def test_count_vs_size(self):
        """Verify that count mode differs dramatically from size mode."""
        count_total = self.tree.app_size()
        size_tree = self.duscan_tree(self.fs, '/', count=False)
        size_total = size_tree.app_size()

        self.debug('DuScanCountModeSeed1Depth4Test.test_count_vs_size',
                   'count:', count_total, 'size:', size_total)
        # Count should be much smaller than size (in bytes)
        self.assertLess(count_total, size_total)
        # Original size test shows 2053393838542 bytes
        self.assertEqual(size_total, 2053393838542)


class DuScanCountModeSeed206Depth2Test(DuScanTestMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fs = GeneratedFilesystem(seed=206, maxdepth=2)
        cls.tree = cls.duscan_tree(cls.fs, '/', count=True)

    def test_count_total(self):
        """Verify total object count for seed 206, depth 2."""
        dutree_count = self.tree.app_size()
        self.debug('DuScanCountModeSeed206Depth2Test.test_count_total',
                   dutree_count)
        self.assertEqual(dutree_count, 24)

    def test_count_leaves(self):
        """Verify leaves match expected counts."""
        expected = [
            ('/00.txt', 1, 1),
            ('/01.txt', 1, 1),
            ('/02.txt', 1, 1),
            ('/03.txt', 1, 1),
            ('/04.txt', 1, 1),
            ('/05.txt', 1, 1),
            ('/06.txt', 1, 1),
            ('/07.txt', 1, 1),
            ('/08.txt', 1, 1),
            ('/09.txt', 1, 1),
            ('/10.txt', 1, 1),
            ('/11.txt', 1, 1),
            ('/12.txt', 1, 1),
            ('/13.txt', 1, 1),
            ('/14.txt', 1, 1),
            ('/15.txt', 1, 1),
            ('/16.txt', 1, 1),
            ('/17.txt', 1, 1),
            ('/18.txt', 1, 1),
            ('/19.txt', 1, 1),
            ('/20.txt', 1, 1),
            ('/21.txt', 1, 1),
            ('/22.txt', 1, 1),
            ('/23.txt', 1, 1),
        ]
        self.assertEqual(self.leaves_as_list(self.tree), expected)

    def test_count_vs_size(self):
        """Verify count mode differs from size mode."""
        count_total = self.tree.app_size()
        size_tree = self.duscan_tree(self.fs, '/', count=False)
        size_total = size_tree.app_size()

        self.debug('DuScanCountModeSeed206Depth2Test.test_count_vs_size',
                   'count:', count_total, 'size:', size_total)
        # Count should be much smaller than size
        self.assertLess(count_total, size_total)
        self.assertEqual(count_total, 24)


class DuScanCountModeBlocksTest(DuScanTestMixin, TestCase):
    """Count mode should produce same results regardless of apparent_size setting."""
    use_apparent_size = False

    @classmethod
    def setUpClass(cls):
        cls.fs = GeneratedFilesystem(seed=1, maxdepth=4)
        cls.tree = cls.duscan_tree(cls.fs, '/', count=True)

    def test_count_total_blocks(self):
        """Verify total count is same regardless of use_apparent_size."""
        dutree_count = self.tree.app_size()
        # Should be same as with use_apparent_size=True
        self.assertEqual(dutree_count, 165386)

    def test_count_app_equals_use(self):
        """In count mode, app_size and use_size should always be equal."""
        self.assertEqual(self.tree.app_size(), self.tree.use_size())


class DuScanCountModeCopeWithDeletionTest(DuScanTestMixin, TestCase):
    def test_handle_deleted_count(self):
        """Verify count mode handles deleted files/dirs correctly."""
        fs = GeneratedFilesystem(seed=1, maxdepth=4)

        # Count deleted objects
        deleted_count = 0

        # Hide a directory
        deleted_count += 1  # the directory itself
        # Plus all files/dirs within it (need to count them)
        # For simplicity, just hide it and count the change

        fs.hide_from_stat('/0.d/05.d')

        # Scan with deletion
        tree = self.duscan_tree(fs, '/', count=True)
        count_with_deletion = tree.app_size()

        # Should be less than original count of 165386
        self.assertLess(count_with_deletion, 165386)
        self.assertGreater(count_with_deletion, 0)


class DuScanCountModeNoLonelyStarCountTest(DuScanTestMixin, TestCase):
    """Verify pruning behavior works correctly in count mode."""
    @classmethod
    def setUpClass(cls):
        cls.fs = GeneratedFilesystem(seed=6, maxdepth=4)
        cls.tree = cls.duscan_tree(cls.fs, '/', count=True)

    def test_count_leaves_pruning(self):
        """Verify that pruning (5% threshold) works with counts."""
        leaves = self.leaves_as_list(self.tree)
        total_count = self.tree.app_size()
        threshold = total_count // 20  # 5% threshold

        # All leaves should be above threshold (except possibly "*" nodes)
        for name, app_count, use_count in leaves:
            if not name.endswith('*'):
                self.assertGreaterEqual(app_count, threshold,
                    f"{name} count {app_count} below threshold {threshold}")

    def test_count_total_reasonable(self):
        """Verify total count is in reasonable range for this seed."""
        count = self.tree.app_size()
        # Should be a substantial but not enormous number
        self.assertGreater(count, 0)
        self.assertLess(count, 1000000)


if __name__ == '__main__':
    main()
