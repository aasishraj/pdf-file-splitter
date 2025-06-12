import PyPDF2

def split_pdf_by_range(input_path, output_path, start_page, end_page):
    with open(input_path, 'rb') as infile:
        reader = PyPDF2.PdfReader(infile)
        writer = PyPDF2.PdfWriter()

        for i in range(start_page - 1, end_page):
            if i < len(reader.pages):
                writer.add_page(reader.pages[i])

        with open(output_path, 'wb') as outfile:
            writer.write(outfile)