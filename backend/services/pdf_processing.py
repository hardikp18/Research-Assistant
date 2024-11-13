# backend/services/pdf_processing.py
import fitz  # PyMuPDF
import requests
import io
import base64
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class PDFProcessingService:
    def __init__(self):
        self.session = requests.Session()
        
    async def process_pdf_url(self, url: str) -> Optional[Dict]:
        """Download and process PDF from URL"""
        try:
            # Download PDF
            response = self.session.get(url)
            response.raise_for_status()
            
            # Load PDF
            pdf_stream = io.BytesIO(response.content)
            doc = fitz.open(stream=pdf_stream, filetype="pdf")
            
            text_content = []
            images = []
            
            # Extract text and images
            for page_num, page in enumerate(doc):
                # Get text
                text_content.append(page.get_text())
                
                # Get images
                for img_index, img in enumerate(page.get_images()):
                    xref = img[0]
                    base_img = doc.extract_image(xref)
                    image_data = base64.b64encode(base_img["image"]).decode()
                    
                    images.append({
                        "page": page_num + 1,
                        "index": img_index + 1,
                        "type": base_img["ext"],
                        "data": image_data
                    })
            
            return {
                "text": "\n\n".join(text_content),
                "images": images
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF from {url}: {e}")
            return None
        finally:
            if 'doc' in locals():
                doc.close()