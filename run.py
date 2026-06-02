"""Jalankan server TutorQA."""
import uvicorn

HOST = "127.0.0.1"
PORT = 8000

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  TutorQA — server aktif")
    print("=" * 50)
    print(f"  Buka di browser:  http://localhost:{PORT}")
    print(f"  Panduan:          http://localhost:{PORT}/panduan")
    print("  (Jangan gunakan 0.0.0.0 di browser)")
    print("=" * 50 + "\n")

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=True,
    )
