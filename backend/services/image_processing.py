# services/image_processing.py
from typing import List
import easyocr
from PIL import Image
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageProcessingService:
    def __init__(self):
        self.reader = easyocr.Reader(['en'])

    def extract_image_text(self, image: Image.Image) -> str:
        """Extract text from image using OCR"""
        try:
            # Convert PIL Image to numpy array
            img_np = np.array(image)
            
            # Use EasyOCR to detect text
            results = self.reader.readtext(img_np)
            
            # Combine all detected text
            text = ' '.join([result[1] for result in results])
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return ""

# Create instance for import
image_processor = ImageProcessingService()
extract_image_text = image_processor.extract_image_text