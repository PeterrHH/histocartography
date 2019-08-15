"""Unit test for complex_module.core."""
import unittest
from histocartography.io.wsi import WSI
from histocartography.io.utils import get_s3
from histocartography.io.utils import download_file_to_local
from PIL import Image
import numpy as np


class CoreTestCase(unittest.TestCase):
    """CoreTestCase class."""

    def setUp(self):
        """Setting up the test."""
        s3_resource = get_s3()
        filename = download_file_to_local(s3= s3_resource, bucket_name= 'datasets', 
                                        s3file= 'prostate/biopsy_data_all/17/17.tif',
                                        local_name='tmp/00_biopsy.tif'
                                        )
        annotation_file = download_file_to_local(s3= s3_resource, bucket_name= 'datasets', 
                                        s3file= 'prostate/biopsy_data_all/17/17.xml',
                                        local_name='tmp/01_biopsy.xml'
                                        )
        self.wsi = WSI(wsi_file=filename, annotation_file=annotation_file)
        pass

    def test_image_at(self):
        """Test image_at."""


        image5x = self.wsi.image_at(5)
        self.assertAlmostEqual(5, self.wsi.current_magnification)
        
        image2_5x = self.wsi.image_at(2.5)
        self.assertAlmostEqual(2.5, self.wsi.current_magnification)
        Image.fromarray(image2_5x).save("tmp/02_biopsy_2.5x.png")

    def test_tissue_mask(self):
        """Test tissue_mask_at."""

        tissue_mask = self.wsi.tissue_mask_at(2.5)
        Image.fromarray(tissue_mask).save("tmp/03_tissue_mask_2.5x.png")

    def test_annotation_mask(self):
        """Test annotation_mask_at."""

        annotation_mask = self.wsi.annotation_mask_at(2.5)
        annotation_mask = np.uint8(annotation_mask*255 / np.max(annotation_mask))

        Image.fromarray(annotation_mask).save("tmp/04_annotation_mask_2.5x.png")

    def tearDown(self):
        """Tear down the tests."""
        self.wsi.stack.close()
        pass
