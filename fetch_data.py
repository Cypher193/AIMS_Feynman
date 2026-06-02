import os
import fitz  # PyMuPDF

PDF_DIR = "./pdf_source"
OUTPUT_DIR = "./data/official_lectures"

def convert_pdfs_to_text():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not os.path.exists(PDF_DIR) or not os.listdir(PDF_DIR):
        print(f"Error: Please download the PDFs from the repository and place them in '{PDF_DIR}' first.")
        return

    print("--- Starting PDF Layout Extraction ---")
    for filename in sorted(os.listdir(PDF_DIR)):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(PDF_DIR, filename)
            txt_filename = filename.replace(".pdf", ".txt")
            txt_path = os.path.join(OUTPUT_DIR, txt_filename)
            
            print(f"Extracting text from {filename}...")
            try:
                doc = fitz.open(pdf_path)
                full_text = []
                
                for page_num, page in enumerate(doc):
                    # "text" block extraction preserves paragraph flow better than standard line clipping
                    page_text = page.get_text("text")
                    full_text.append(f"\n--- Page {page_num + 1} ---\n")
                    full_text.append(page_text)
                
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(full_text))
                    
                print(f"Successfully saved clean text to {txt_path}")
                
            except Exception as e:
                print(f"Failed to process {filename}: {e}")
                
    print("\n--- Processing Complete! Your data folder is fully populated. ---")

if __name__ == "__main__":
    convert_pdfs_to_text()