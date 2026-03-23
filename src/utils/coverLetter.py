# Windows-only: search/replace in Word, export PDF, then open PDF with default app
import os, platform
import shutil
from pathlib import Path
import re
import win32com.client as win32
import win32com
import json

def open_with_default_app(path: Path):
    # from the Stack Overflow pattern: Windows uses os.startfile
    if platform.system() == "Windows":
        os.startfile(str(path))  # opens with default associated app

class CoverLetterPDF:

    def __init__(self):
        self.input_docx_folder = r"document_folder"
        self.job_type=r"A1-Cover Letter -- <replace>.docx"
        self.out_dir=os.path.join(self.input_docx_folder, "submitted")

    def _create_word_app(self):
        """
        Create Word COM app with recovery for corrupted win32com gen_py cache.
        """
        try:
            return win32.gencache.EnsureDispatch("Word.Application")
        except Exception as e:
            err_text = str(e)
            if "MinorVersion" not in err_text and "gen_py" not in err_text:
                raise

            # Recover from stale/corrupted generated COM cache, then use late binding.
            try:
                gen_path = Path(win32com.__gen_path__)
                if gen_path.exists():
                    shutil.rmtree(gen_path, ignore_errors=True)
            except Exception:
                pass

            try:
                win32.gencache.is_readonly = False
                win32.gencache.Rebuild()
            except Exception:
                pass

            return win32.Dispatch("Word.Application")

    def word_replace_to_pdf_win(self, input_docx, replacements: dict, out_dir, target_name):
        input_docx = Path(input_docx).resolve()
        out_dir = Path(out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        output_pdf = out_dir / f"{target_name}.pdf"

        wdReplaceAll = 2 # means replace all occurrences, 1 means replace only first occurrence
        wdFormatPDF  = 17 # save as pdf format, 16 means save as docx format
        print(replacements)

        word = self._create_word_app()
        word.Visible = False  # set True if you want to watch Word
        doc = None
        try:
            doc = word.Documents.Open(str(input_docx))

            # Run replacement across all Word story ranges (body, headers/footers,
            # text boxes, shapes). Using only doc.Content can miss visible text.
            for old, new in replacements.items():
                story = doc.StoryRanges(1)
                while story is not None:
                    find = story.Find
                    find.ClearFormatting()
                    find.Replacement.ClearFormatting()
                    find.Execute(
                        FindText=str(old),
                        ReplaceWith=str(new),
                        Replace=wdReplaceAll,
                        Forward=True,
                        Wrap=1,
                        Format=False,
                        MatchCase=False,
                        MatchWholeWord=False,
                        MatchWildcards=False,
                        MatchSoundsLike=False,
                        MatchAllWordForms=False,
                    )
                    try:
                        story = story.NextStoryRange
                    except Exception:
                        story = None

            doc.Save()

            # Export directly to PDF at your specific path/name
            doc.SaveAs2(str(output_pdf), FileFormat=wdFormatPDF)
        finally:
            # Clean up
            if doc is not None:
                doc.Close(False)
            word.Quit()

        # Preview result using default OS app (Windows uses os.startfile)
        # open_with_default_app(output_pdf)
        return output_pdf

    def load_history(self, selected_idx: int):
        recorded_last_job_name_path = r"./env/cover_letter_last_job.json"
        load_data = dict()
        with open(recorded_last_job_name_path, "r", encoding="utf-8") as f:
            load_data: dict = json.load(f)
        normalized_idx = self._normalize_selected_index(selected_idx)
        return load_data.get(normalized_idx)

    def instant_save(self, data: dict):
        recorded_last_job_name_path = r"./env/cover_letter_last_job.json"
        with open(recorded_last_job_name_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def _update_history_after_generate(self, selected_idx, company_name: str, job_title: str):
        recorded_last_job_name_path = r"./env/cover_letter_last_job.json"
        normalized_idx = self._normalize_selected_index(selected_idx)

        try:
            with open(recorded_last_job_name_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        if not isinstance(data.get(normalized_idx), dict):
            data[normalized_idx] = {}

        data[normalized_idx]["company_name"] = company_name
        data[normalized_idx]["position_name"] = job_title

        self.instant_save(data)

    def _normalize_selected_index(self, selected_idx) -> str:
        # GPT may return values like "A", "a", "A.", "A)"; normalize to A-F style key.
        idx = str(selected_idx).strip().upper()
        m = re.match(r"^[A-Z]", idx)
        if m:
            return m.group(0)
        return idx

    def _build_replacements(self, selected_idx, company_name: str, job_title: str) -> dict:
        loaded_history = self.load_history(selected_idx)

        if not isinstance(loaded_history, dict):
            raise ValueError(f"No cover letter history found for selected index: {selected_idx}")

        old_company = str(loaded_history.get("company_name", "")).strip()
        old_position = str(loaded_history.get("position_name", "")).strip()

        replacements = {}
        if old_company:
            replacements[old_company] = company_name
        if old_position:
            replacements[old_position] = job_title

        if not replacements:
            raise ValueError(f"Invalid history payload for selected index: {selected_idx}")

        return replacements

    # Example
    def load_and_generate(self, job_info: dict):
        company_name, job_title, file_suffix, selected_idx = job_info["company"], job_info["title"], job_info["selected_document"], job_info["selected_document_index"]
        resume, coverLetter = file_suffix
        replacements = self._build_replacements(selected_idx, company_name, job_title)
        
        input_docx = os.path.join(self.input_docx_folder, self.job_type.replace("<replace>", coverLetter))
        self.pdf = self.word_replace_to_pdf_win(
            input_docx=input_docx,
            replacements=replacements,
            out_dir=self.out_dir,
            target_name=f"Cover Letter {company_name}"
        )
        # Convert to absolute path for Selenium file upload
        self.resume_path = os.path.abspath(os.path.join(self.input_docx_folder, resume+".pdf"))

        # Persist latest company/title for the selected template bucket (A-F).
        self._update_history_after_generate(selected_idx, company_name, job_title)
        
        print(f"resume path: {self.resume_path} \ncover letter path: {self.pdf}")
    
    def get_cover_letter_path(self):
        return self.pdf
    
    def get_resume_path(self):
        return self.resume_path