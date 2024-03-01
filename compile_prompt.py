def read_file_content(file_name):
    with open(file_name, 'r') as file:
        content = file.read()
    return content

def get_prompt():
    # Read content from report.pdf
    try:
        import PyPDF2
        pdf_file_path = './input/report.pdf'
        pdf_content = ''
        
        with open(pdf_file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            num_pages = len(pdf_reader.pages)
            for page_number in range(num_pages):
                page = pdf_reader.pages[page_number]
                pdf_content += page.extract_text()
    except ImportError:
        print("PyPDF2 library is not installed. Please install it using 'pip install PyPDF2'.")
        pdf_content = ''

    # Read content from instructions.txt
    instruction_file_path = 'instruction.txt'
    instruction_content = read_file_content(instruction_file_path)

    # Append PDF content to instruction content
    combined_content = instruction_content + '\n\n' + pdf_content

    # Print or use the combined content as needed
    print(combined_content)

    return combined_content
