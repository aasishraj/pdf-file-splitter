import argparse

from splitter import split_pdf_by_range

def main():
    parser = argparse.ArgumentParser(description='Split a range of pages from a PDF.')
    parser.add_argument('input', help='Path to the input PDF file')
    parser.add_argument('output', help='Path to the output PDF file')
    parser.add_argument('start', type=int, help='Start page number (1-based)')
    parser.add_argument('end', type=int, help='End page number (inclusive, 1-based)')

    args = parser.parse_args()

    split_pdf_by_range(args.input, args.output, args.start, args.end)

if __name__ == '__main__':
    main()
