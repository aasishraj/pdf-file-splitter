import PyPDF2

def split_pdf_by_range(input_path, output_path, start_page, end_page):
    with open(input_path, 'rb') as infile:
        reader = PyPDF2.PdfReader(infile)
        writer = PyPDF2.PdfWriter()
        
        total_pages = len(reader.pages)
        
        # Validate start_page
        if start_page < 1:
            raise ValueError("start_page must be at least 1")
        if start_page > total_pages:
            raise ValueError(f"start_page ({start_page}) exceeds total pages ({total_pages})")
        
        # Handle end_page - if None or greater than total pages, use total pages
        if end_page is None or end_page > total_pages:
            end_page = total_pages
        
        # Validate end_page
        if end_page < start_page:
            raise ValueError("end_page must be greater than or equal to start_page")
        
        # Extract pages (making end_page inclusive)
        for i in range(start_page - 1, end_page):  # end_page is now properly bounded
            writer.add_page(reader.pages[i])

        with open(output_path, 'wb') as outfile:
            writer.write(outfile)