import sys
import os
from src.gui.main_window import WeChatAnalyzerGUI
import tkinter as tk

def main():
    root = tk.Tk()
    app = WeChatAnalyzerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 