
from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.cell(200, 10, txt="RAG Test Document", ln=1, align="C")
pdf.cell(200, 10, txt="This is a test document for the RAG system.", ln=2, align="L")
pdf.cell(200, 10, txt="The capital of France is Paris.", ln=3, align="L")
pdf.cell(200, 10, txt="Python is a popular programming language.", ln=4, align="L")
pdf.cell(200, 10, txt="ChromaDB is a vector database.", ln=5, align="L")

pdf.output("test_rag.pdf")
print("test_rag.pdf created.")
