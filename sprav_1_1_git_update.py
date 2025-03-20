import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
import json
import os
import sys
import keyboard
import requests


class GlossaryApp:

    def __init__(self, root):
        super().__init__()
        self.root = root
        self.root.title("Справочник")
        self.root.geometry("900x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.appearance_mode = "System"
        ctk.set_appearance_mode(self.appearance_mode)

        if getattr(sys, 'frozen', False):
            self.data_directory = os.path.dirname(sys.executable)
        else:
            self.data_directory = os.path.dirname(os.path.abspath(__file__))
        
        self.glossaries = {}
        self.current_glossary = None
        self.open_tabs = set()  
        self.notebook = ctk.CTkTabview(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.notebook.configure(command=self.notebook_tab_changed)

        self.menu_bar = ctk.CTkFrame(root)
        self.menu_bar.pack(side="top", fill="x")

        self.file_menu = ctk.CTkOptionMenu(self.menu_bar, values=["Новый", "Открыть", "Сохранить", "Сохранить как...", "Выход"],
                                            command=self.file_menu_callback, font=ctk.CTkFont(size=13))
        self.file_menu.pack(side="left", padx=5)

        self.edit_menu = ctk.CTkOptionMenu(self.menu_bar, values=["Добавить термин", "Редактировать термин", "Удалить термин"],
                                            command=self.edit_menu_callback, font=ctk.CTkFont(size=13))
        self.edit_menu.pack(side="left", padx=5)

        self.appearance_menu = ctk.CTkOptionMenu(self.menu_bar, values=["System", "Dark", "Light"],
                                                 command=self.change_appearance_mode, font=ctk.CTkFont(size=13))
        self.appearance_menu.set(self.appearance_mode)
        self.appearance_menu.pack(side="left", padx=5)
        
        self.download_menu_o_b = ctk.CTkButton(self.menu_bar, text="Загрузить файл", command=self.downlad_menu,font=ctk.CTkFont(size=14))
        self.download_menu_o_b.pack(side="left", padx=5)

        self.search_frame = ctk.CTkFrame(root)
        self.search_frame.pack(side="bottom", fill="x", pady=5, padx=10)

        self.search_label = ctk.CTkLabel(self.search_frame, text="Поиск:", font=ctk.CTkFont(size=14))
        self.search_label.pack(side="left", padx=5)

        self.search_entry = ctk.CTkEntry(self.search_frame, font=ctk.CTkFont(size=14))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.search_button = ctk.CTkButton(self.search_frame, text="Найти", command=self.search_term_all_files, font=ctk.CTkFont(size=14))
        self.search_button.pack(side="left", padx=5)

        keyboard.add_hotkey("F9", self.toggle_visibility)
        self.root.bind("<Control-f>", self.focus_search_entry)

        self.load_glossaries()

        self.is_modified = False
        self.is_visible = False

        self.search_results = []
        self.current_search_index = -1

        self.search_results_window = None
        self.search_result_text = None
        self.result_navigation_frame = None
        self.result_index_label = None
        self.next_result_button = None
        self.prev_result_button = None
        
    def button_callback(self, file):
        git_url = "https://raw.githubusercontent.com/mrHolaDays/fast_guide_app/refs/heads/guides/"
        resp = requests.get(f"{git_url}/{file}")
        if resp.status_code == 200:
            with open(file, "wb") as file:
                file.write(resp.content)
            self.load_glossaries()

        
    def downlad_menu(self):
        git_url = "https://raw.githubusercontent.com/mrHolaDays/fast_guide_app/refs/heads/guides/"
        self.downlad_menu_window = ctk.CTkToplevel(self.root)
        self.downlad_menu_window.title("Загрузка справочников")
        self.downlad_menu_window.geometry("600x400")
        
        response = requests.get(f"{git_url}/list.txt")
        if response.status_code == 200:
            f_cont = response.text
            file_l = f_cont.split("\n")
            
            file_list = [e.split("$") for e in file_l]
            
            
            for i in file_list:
                if len(i) == 3 and i[2].strip(): 
                    file_frame = ctk.CTkFrame(self.downlad_menu_window)
                    file_frame.pack(fill="x", padx=10, pady=5)
                    
                    
                    title_label = ctk.CTkLabel(file_frame, text=i[0], font=ctk.CTkFont(size=16, weight="bold"))
                    title_label.pack(anchor="w", padx=5, pady=2)
                    
                    
                    description_label = ctk.CTkLabel(file_frame, text=i[1], font=ctk.CTkFont(size=14))
                    description_label.pack(anchor="w", padx=5, pady=2)
                    

                    download_button = ctk.CTkButton(file_frame,text="Скачать",command=lambda idx=i: self.button_callback(idx[2]))
                    download_button.pack(side="right", padx=5, pady=5)
        
    def focus_search_entry(self, event=None):
        self.search_entry.focus_set()
        return "break"

    def file_menu_callback(self, choice):
        if choice == "Новый":
            self.create_new_glossary()
        elif choice == "Открыть":
            self.open_glossary()
        elif choice == "Сохранить":
            self.save_current_glossary()
        elif choice == "Сохранить как...":
            self.save_glossary_as()
        elif choice == "Выход":
            self.on_closing()

    def edit_menu_callback(self, choice):
        if choice == "Добавить термин":
            self.add_term()
        elif choice == "Редактировать термин":
            self.edit_term()
        elif choice == "Удалить термин":
            self.delete_term()

    def change_appearance_mode(self, new_mode):
        self.appearance_mode = new_mode
        ctk.set_appearance_mode(self.appearance_mode)

    def toggle_visibility(self):
        if self.is_visible:
            self.root.withdraw()
            self.is_visible = False
        else:
            self.root.deiconify()
            self.is_visible = True

    def load_glossaries(self):
        for filename in os.listdir(self.data_directory):
            if filename.endswith(".json"):
                filepath = os.path.join(self.data_directory, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.glossaries[filename] = data
                        
                        
                        tab_name = filename[:-5]  
                        if tab_name not in self.open_tabs:
                            
                            self.create_tab(filename)
                            self.open_tabs.add(tab_name) 
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось загрузить файл {filename}: {e}")
    def create_tab(self, filename):
        tab_name = filename[:-5]
        self.notebook.add(tab_name)
        text_area = ctk.CTkTextbox(self.notebook.tab(tab_name), wrap="word", font=ctk.CTkFont(size=14), border_spacing=5)
        text_area.pack(fill="both", expand=True)
        text_area.configure(state="disabled")
        self.notebook.tab(tab_name).text_area = text_area

    def create_new_glossary(self):
        filename = simpledialog.askstring("Новый файл", "Введите имя нового файла (без расширения .json):")
        if filename:
            filename = filename + ".json"
            filepath = os.path.join(self.data_directory, filename)
            if os.path.exists(filepath):
                messagebox.showerror("Ошибка", "Файл с таким именем уже существует.")
                return

            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=4, ensure_ascii=False)
                self.glossaries[filename] = {}
                self.create_tab(filename)
                self.notebook.set(filename[:-5])
                self.notebook_tab_changed()
                self.is_modified = False
                messagebox.showinfo("Успех", "Файл создан.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать файл: {e}")

    def open_glossary(self):
        filepath = filedialog.askopenfilename(initialdir=self.data_directory, filetypes=[("JSON files", "*.json")])
        if filepath:
            filename = os.path.basename(filepath)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    
                    tab_name = filename[:-5]  
                    if tab_name not in self.open_tabs:
                        
                        self.glossaries[filename] = data
                        self.create_tab(filename)
                        self.open_tabs.add(tab_name)  
                    else:
                        
                        self.glossaries[filename] = data
                        self.display_glossary_data(self.notebook.tab(tab_name).text_area)
                    
                    
                    self.notebook.set(tab_name)
                    self.notebook_tab_changed()
                    self.is_modified = False
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")

    def save_glossary_as(self):
        filepath = filedialog.asksaveasfilename(initialdir=self.data_directory, defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(self.glossaries[self.current_glossary], f, indent=4, ensure_ascii=False)

                new_filename = os.path.basename(filepath)
                old_filename = self.current_glossary
                self.glossaries[new_filename] = self.glossaries.pop(old_filename)
                self.current_glossary = new_filename

                current_tab = self.notebook.get()
                self.notebook.rename_tab(current_tab, new_filename[:-5])
                self.is_modified = False
                messagebox.showinfo("Успех", "Файл сохранен.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    def save_current_glossary(self, event=None):
        if self.current_glossary:
            filepath = os.path.join(self.data_directory, self.current_glossary)
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(self.glossaries[self.current_glossary], f, indent=4, ensure_ascii=False)
                self.is_modified = False
                messagebox.showinfo("Успех", "Файл сохранен.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    def notebook_tab_changed(self):
        selected_tab = self.notebook.get()
        if selected_tab:
            text_area = self.notebook.tab(selected_tab).text_area
            tab_text = selected_tab + ".json"
            if tab_text in self.glossaries:
                self.current_glossary = tab_text
                self.display_glossary_data(text_area)
            else:
                self.current_glossary = None
                text_area.configure(state="normal")
                text_area.delete("1.0", "end")
                text_area.configure(state="disabled")
                messagebox.showerror("Ошибка", "Файл не найден")
        else:
            self.current_glossary = None

    def display_glossary_data(self, text_area):
        text_area.configure(state="normal")
        text_area.delete("1.0", "end")

        if self.current_glossary:
            data = self.glossaries[self.current_glossary]

            title_font = ctk.CTkFont(size=18, weight="bold")
            term_font = ctk.CTkFont(size=16, weight="bold")
            definition_font = ctk.CTkFont(size=14)

            filename = self.current_glossary[:-5]
            text_area.insert("1.0", f"{filename}\n", title_font)
            text_area.insert("end", "-" * len(filename) + "\n")

            for term, definition in data.items():
                text_area.insert("end", f"{term}\n", term_font)
                if isinstance(definition, (dict, list)):
                    definition_str = json.dumps(definition, indent=4, ensure_ascii=False)
                else:
                    definition_str = str(definition)
                text_area.insert("end", f"{definition_str}\n\n", definition_font)

            text_area.configure(state="disabled")

    def recursive_search(self, data, path="", filename=""):
        results = []
        if isinstance(data, dict):
            for key, value in data.items():
                key_str = str(key).lower()
                if self.search_entry.get().lower() in key_str:
                    results.append((filename, f"{path}.{key}" if path else key, data[key]))
                if isinstance(value, (str, int, float)):
                    value_str = str(value).lower()
                    if self.search_entry.get().lower() in value_str:
                        results.append((filename, f"{path}.{key}" if path else key, value))
                elif isinstance(value, (dict, list)):
                    results.extend(self.recursive_search(value, f"{path}.{key}" if path else key, filename))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (str, int, float)):
                    item_str = str(item).lower()
                    if self.search_entry.get().lower() in item_str:
                        results.append((filename, f"{path}[{i}]" if path else f"[{i}]", item))
                elif isinstance(item, (dict, list)):
                    results.extend(self.recursive_search(item, f"{path}[{i}]" if path else f"[{i}]", filename))
        return results

    def search_term_all_files(self):
        search_term = self.search_entry.get().lower()
        self.search_results = []
        self.current_search_index = -1

        for filename, data in self.glossaries.items():
            results_for_file = self.recursive_search(data, filename=filename)
            self.search_results.extend(results_for_file)

        if self.search_results:
            self.current_search_index = 0
            self.show_search_results_window()
            self.update_search_result_display()
        else:
            messagebox.showinfo("Информация", "Совпадений не найдено.")

    def show_search_results_window(self):
        if self.search_results_window is None or not self.search_results_window.winfo_exists():
            self.search_results_window = ctk.CTkToplevel(self.root)
            self.search_results_window.title("Результаты поиска")
            self.search_results_window.geometry("600x400")
            self.search_results_window.protocol("WM_DELETE_WINDOW", self.close_search_results_window)

            self.search_result_text = ctk.CTkTextbox(self.search_results_window, wrap="word", font=ctk.CTkFont(size=14))
            self.search_result_text.pack(fill="both", expand=True, padx=10, pady=5)

            self.result_navigation_frame = ctk.CTkFrame(self.search_results_window)
            self.result_navigation_frame.pack(fill="x", padx=10, pady=5)

            self.prev_result_button = ctk.CTkButton(self.result_navigation_frame, text="<- Previous", command=self.show_previous_result, font=ctk.CTkFont(size=14))
            self.prev_result_button.pack(side="left", padx=5)

            self.result_index_label = ctk.CTkLabel(self.result_navigation_frame, text="", font=ctk.CTkFont(size=14))
            self.result_index_label.pack(side="left", padx=5)

            self.next_result_button = ctk.CTkButton(self.result_navigation_frame, text="Next ->", command=self.show_next_result, font=ctk.CTkFont(size=14))
            self.next_result_button.pack(side="left", padx=5)
            self.update_search_result_display()

    def close_search_results_window(self):
        if self.search_results_window:
            self.search_results_window.destroy()
            self.search_results_window = None
            self.search_result_text = None
            self.result_navigation_frame = None
            self.result_index_label = None
            self.next_result_button = None
            self.prev_result_button = None

    def update_search_result_display(self):
        if not self.search_results_window or not self.search_results:
            return

        self.search_result_text.configure(state="normal")
        self.search_result_text.delete("1.0", "end")

        if 0 <= self.current_search_index < len(self.search_results):
            filename, path, value = self.search_results[self.current_search_index]
            display_text = f"Файл: {filename}\n"
            if value is not None:
                display_text += f"Путь: {path}\nЗначение:\n"
                if isinstance(value, (dict, list)):
                    display_text += json.dumps(value, indent=4, ensure_ascii=False) + "\n"
                else:
                    display_text += str(value) + "\n"
            else:
                display_text += f"Ключ: {path.split('.')[-1] if '.' in path else path}\n"

            self.search_result_text.insert("1.0", display_text)
        self.search_result_text.configure(state="disabled")

        self.result_index_label.configure(text=f"Результат {self.current_search_index + 1} из {len(self.search_results)}")
        self.update_navigation_buttons()

    def update_navigation_buttons(self):
        if self.prev_result_button:
            self.prev_result_button.configure(state="normal" if self.current_search_index > 0 else "disabled")
        if self.next_result_button:
            self.next_result_button.configure(state="normal" if self.current_search_index < len(self.search_results) - 1 else "disabled")

    def show_next_result(self):
        if 0 <= self.current_search_index < len(self.search_results) - 1:
            self.current_search_index += 1
            self.update_search_result_display()

    def show_previous_result(self):
        if 0 < self.current_search_index < len(self.search_results):
            self.current_search_index -= 1
            self.update_search_result_display()

    def add_term(self):
        if not self.current_glossary:
            messagebox.showinfo("Информация", "Откройте файл для редактирования.")
            return

        def add_term_callback():
            term = term_entry.get()
            definition = definition_entry.get("1.0", "end").strip()

            if not term or not definition:
                messagebox.showerror("Ошибка", "Поля не могут быть пустыми.")
                return

            try:
                term_json = json.loads(term)
                definition_json = json.loads(definition)
                self.glossaries[self.current_glossary][term] = definition
            except json.JSONDecodeError:
                self.glossaries[self.current_glossary][term] = definition

            try:
                self.display_glossary_data()
                self.save_current_glossary()
                add_term_window.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось добавить термин: {e}")

        add_term_window = ctk.CTkToplevel(self.root)
        add_term_window.title("Добавить термин")
        add_term_window.geometry("400x300")

        term_label = ctk.CTkLabel(add_term_window, text="Термин (JSON):", font=ctk.CTkFont(size=14))
        term_label.pack(pady=5)
        term_entry = ctk.CTkEntry(add_term_window, font=ctk.CTkFont(size=14))
        term_entry.pack(padx=10, pady=5, fill="x")

        definition_label = ctk.CTkLabel(add_term_window, text="Определение (JSON):", font=ctk.CTkFont(size=14))
        definition_label.pack(pady=5)
        definition_entry = ctk.CTkTextbox(add_term_window, wrap="word", height=8, font=ctk.CTkFont(size=14))
        definition_entry.pack(padx=10, pady=5, fill="both", expand=True)

        add_button = ctk.CTkButton(add_term_window, text="Добавить", command=add_term_callback, font=ctk.CTkFont(size=14))
        add_button.pack(pady=10)

    def edit_term(self):
        if not self.current_glossary:
            messagebox.showinfo("Информация", "Откройте файл для редактирования.")
            return

        terms = list(self.glossaries[self.current_glossary].keys())
        if not terms:
            messagebox.showinfo("Информация", "Нет терминов для редактирования.")
            return

        def edit_term_callback():
            selected_term = term_listbox.get(term_listbox.curselection()[0]) if term_listbox.curselection() else None

            if not selected_term:
                messagebox.showinfo("Информация", "Выберите термин для редактирования.")
                return

            def update_term_callback():
                new_definition = definition_entry.get("1.0", "end").strip()

                if not new_definition:
                    messagebox.showerror("Ошибка", "Определение не может быть пустым.")
                    return

                try:
                    new_definition_json = json.loads(new_definition)
                    self.glossaries[self.current_glossary][selected_term] = new_definition
                except json.JSONDecodeError:
                    self.glossaries[self.current_glossary][selected_term] = new_definition

                try:
                    self.display_glossary_data()
                    self.save_current_glossary()
                    edit_term_window.destroy()
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось обновить термин: {e}")

            edit_term_window = ctk.CTkToplevel(self.root)
            edit_term_window.title(f"Редактировать {selected_term}")
            edit_term_window.geometry("400x300")

            definition_label = ctk.CTkLabel(edit_term_window, text="Определение (JSON):", font=ctk.CTkFont(size=14))
            definition_label.pack(pady=5)
            definition_entry = ctk.CTkTextbox(edit_term_window, wrap="word", height=8, font=ctk.CTkFont(size=14))
            definition_entry.insert("1.0", self.glossaries[self.current_glossary][selected_term])
            definition_entry.pack(padx=10, pady=5, fill="both", expand=True)

            update_button = ctk.CTkButton(edit_term_window, text="Обновить", command=update_term_callback, font=ctk.CTkFont(size=14))
            update_button.pack(pady=10)

        edit_term_window = ctk.CTkToplevel(self.root)
        edit_term_window.title("Редактировать термин")
        edit_term_window.geometry("300x300")

        term_label = ctk.CTkLabel(edit_term_window, text="Выберите термин:", font=ctk.CTkFont(size=14))
        term_label.pack(pady=5)

        term_listbox = ctk.CTkListbox(edit_term_window, width=280, height=150, font=ctk.CTkFont(size=14))
        for term in terms:
            term_listbox.insert(ctk.END, term)
        term_listbox.pack(padx=10, pady=5)

        edit_button = ctk.CTkButton(edit_term_window, text="Редактировать", command=edit_term_callback, font=ctk.CTkFont(size=14))
        edit_button.pack(pady=10)

    def delete_term(self):
        if not self.current_glossary:
            messagebox.showinfo("Информация", "Откройте файл для редактирования.")
            return

        terms = list(self.glossaries[self.current_glossary].keys())
        if not terms:
            messagebox.showinfo("Информация", "Нет терминов для удаления.")
            return

        def delete_term_callback():
            selected_term_index = term_listbox.curselection()
            if not selected_term_index:
                messagebox.showinfo("Информация", "Выберите термин для удаления.")
                return

            selected_term = term_listbox.get(term_listbox.curselection()[0])

            if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить термин '{selected_term}'?"):
                del self.glossaries[self.current_glossary][selected_term]
                try:
                    self.display_glossary_data()
                    self.save_current_glossary()
                    delete_term_window.destroy()
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось удалить термин: {e}")

        delete_term_window = ctk.CTkToplevel(self.root)
        delete_term_window.title("Удалить термин")
        delete_term_window.geometry("300x300")

        term_label = ctk.CTkLabel(delete_term_window, text="Выберите термин для удаления:", font=ctk.CTkFont(size=14))
        term_label.pack(pady=5)

        term_listbox = ctk.CTkListbox(delete_term_window, width=280, height=150, font=ctk.CTkFont(size=14))
        for term in terms:
            term_listbox.insert(ctk.END, term)
        term_listbox.pack(padx=10, pady=5)

        delete_button = ctk.CTkButton(delete_term_window, text="Удалить", command=delete_term_callback, font=ctk.CTkFont(size=14))
        delete_button.pack(pady=10)

    def on_closing(self):
        if self.is_modified:
            result = messagebox.askyesnocancel("Подтверждение", "Файл был изменен. Сохранить изменения?")
            if result is True:
                self.save_current_glossary()
                self.root.destroy()
            elif result is False:
                self.root.destroy()
            else:
                return
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    app = GlossaryApp(root)
    root.mainloop()