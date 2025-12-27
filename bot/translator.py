# bot/translator.py
import os
import json
import re
import requests
from datetime import datetime
from typing import Optional, Dict, List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class AITranslatorChatbot:
    def __init__(self):
        try:
            self.google_api_key = os.getenv("GOOGLE_API_KEY")
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
            
            if not self.google_api_key:
                raise ValueError("Missing GOOGLE_API_KEY in environment variables.")
            if not self.openai_api_key:
                raise ValueError("Missing OPENAI_API_KEY in environment variables.")

            self.openai_client = OpenAI(api_key=self.openai_api_key)
            self.max_translation_chars = 30000
            self.openai_input_limit = 30000
            self.max_openai_tokens = 2048

            self.supported_languages = {
                'af': 'Afrikaans', 'ak': 'Twi', 'am': 'Amharic', 'ar': 'Arabic', 'as': 'Assamese', 'ay': 'Aymara',
                'az': 'Azerbaijani', 'bm': 'Bambara', 'be': 'Belarusian', 'bn': 'Bengali', 'bho': 'Bhojpuri',
                'bs': 'Bosnian', 'bg': 'Bulgarian', 'ca': 'Catalan', 'ceb': 'Cebuano', 'ny': 'Chichewa',
                'zh': 'Chinese', 'zh-CN': 'Chinese (Simplified)', 'zh-TW': 'Chinese (Traditional)', 'co': 'Corsican',
                'hr': 'Croatian', 'cs': 'Czech', 'da': 'Danish', 'dv': 'Dhivehi', 'doi': 'Dogri', 'nl': 'Dutch',
                'en': 'English', 'eo': 'Esperanto', 'et': 'Estonian', 'ee': 'Ewe', 'fil': 'Filipino', 'fi': 'Finnish',
                'fr': 'French', 'fy': 'Frisian', 'gl': 'Galician', 'ka': 'Georgian', 'de': 'German', 'el': 'Greek',
                'gn': 'Guarani', 'gu': 'Gujarati', 'ht': 'Haitian Creole', 'ha': 'Hausa', 'haw': 'Hawaiian',
                'he': 'Hebrew', 'hi': 'Hindi', 'hmn': 'Hmong', 'hu': 'Hungarian', 'is': 'Icelandic', 'ig': 'Igbo',
                'ilo': 'Ilocano', 'id': 'Indonesian', 'ga': 'Irish', 'it': 'Italian', 'ja': 'Japanese', 'jw': 'Javanese',
                'kn': 'Kannada', 'kk': 'Kazakh', 'km': 'Khmer', 'rw': 'Kinyarwanda', 'gom': 'Konkani', 'ko': 'Korean',
                'kri': 'Krio', 'ku': 'Kurdish (Kurmanji)', 'ckb': 'Kurdish (Sorani)', 'ky': 'Kyrgyz', 'lo': 'Lao',
                'la': 'Latin', 'lv': 'Latvian', 'ln': 'Lingala', 'lt': 'Lithuanian', 'lg': 'Luganda', 'lb': 'Luxembourgish',
                'mk': 'Macedonian', 'mai': 'Maithili', 'mg': 'Malagasy', 'ms': 'Malay', 'ml': 'Malayalam',
                'mt': 'Maltese', 'mi': 'Maori', 'mr': 'Marathi', 'mni-Mtei': 'Meiteilon (Manipuri)', 'lus': 'Mizo',
                'mn': 'Mongolian', 'my': 'Myanmar (Burmese)', 'ne': 'Nepali', 'no': 'Norwegian', 'or': 'Odia (Oriya)',
                'om': 'Oromo', 'ps': 'Pashto', 'fa': 'Persian', 'pl': 'Polish', 'pt': 'Portuguese', 'pa': 'Punjabi',
                'qu': 'Quechua', 'ro': 'Romanian', 'ru': 'Russian', 'sm': 'Samoan', 'sa': 'Sanskrit',
                'gd': 'Scots Gaelic', 'nso': 'Sepedi', 'sr': 'Serbian', 'st': 'Sesotho', 'sn': 'Shona',
                'sd': 'Sindhi', 'si': 'Sinhala', 'sk': 'Slovak', 'sl': 'Slovenian', 'so': 'Somali', 'es': 'Spanish',
                'su': 'Sundanese', 'sw': 'Swahili', 'sv': 'Swedish', 'tg': 'Tajik', 'ta': 'Tamil', 'tt': 'Tatar',
                'te': 'Telugu', 'th': 'Thai', 'ti': 'Tigrinya', 'ts': 'Tsonga', 'tr': 'Turkish', 'tk': 'Turkmen',
                'uk': 'Ukrainian', 'ur': 'Urdu', 'ug': 'Uyghur', 'uz': 'Uzbek', 'vi': 'Vietnamese', 'cy': 'Welsh',
                'xh': 'Xhosa', 'yi': 'Yiddish', 'yo': 'Yoruba', 'zu': 'Zulu', 'br': 'Breton', 'oc': 'Occitan',
                'kmr': 'Northern Kurdish', 'sc': 'Sardinian', 'kl': 'Greenlandic', 'sq': 'Albanian', 'hy': 'Armenian',
                'eu': 'Basque', 'rm': 'Romansh', 'fur': 'Friulian', 'lad': 'Ladino', 'yue': 'Cantonese', 'wuu': 'Shanghainese',
                'hak': 'Hakka', 'nan': 'Min Nan', 'gan': 'Gan', 'cdo': 'Min Dong', 'hsn': 'Xiang', 'bo': 'Tibetan',
                'dz': 'Dzongkha', 'hil': 'Hiligaynon', 'war': 'Waray', 'pam': 'Pampangan', 'bik': 'Bikol', 'pag': 'Pangasinan',
                'smn': 'Inari Sami', 'se': 'Northern Sami', 'sms': 'Skolt Sami', 'sma': 'Southern Sami', 'smj': 'Lule Sami',
                'ba': 'Bashkir', 'cv': 'Chuvash', 'sah': 'Yakut', 'ce': 'Chechen', 'av': 'Avar', 'os': 'Ossetic',
                'kbd': 'Kabardian', 'ady': 'Adyghe', 'lez': 'Lezghian', 'tab': 'Tabasaran', 'kum': 'Kumyk', 'dar': 'Dargwa',
                'inh': 'Ingush', 'tut': 'Altaic', 'sux': 'Sumerian', 'akk': 'Akkadian', 'xal': 'Kalmyk'
            }

            self.conversation_history = []
            
        except Exception as e:
            raise ValueError(f"Initialization failed: {str(e)}")
    
    def get_normal_reply(self, user_input: str) -> str:
        # OpenAI-ভিত্তিক নরমাল চ্যাট রেসপন্স (fallback হিসেবে simple reply)
        try:
            ai_reply = self.get_ai_reply(user_input)
            if ai_reply:
                return ai_reply
        except Exception:
            pass
        return f"I received your message: {user_input}"
    
    def get_ai_reply(self, user_input: str, temperature: float = 0.6, max_tokens: int = 512) -> str:
        """
        Return a normal conversational reply from OpenAI. Falls back to None on errors.
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful, concise assistant."},
                    {"role": "user", "content": user_input}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            content = response.choices[0].message.content.strip()
            # strip code fences if any
            if content.startswith("```") and content.endswith("```"):
                # remove first and last fence
                parts = content.split("\n")
                if len(parts) >= 3:
                    content = "\n".join(parts[1:-1]).strip()
            return content
        except Exception:
            return None

    def smart_text_extraction(self, user_input: str, target_language: str) -> str:
        extraction_prompt = f"""You are a smart text extractor for translation requests. Your job is to identify and extract ONLY the main content that needs to be translated, removing all command words, language specifications, and instructions.


    


User Input: "{user_input}"
Target Language: {target_language}

Rules:
1. Extract ONLY the actual content that needs to be translated.
2. Remove ALL command words like: translate, traduire, অনুবাদ, ترجم, etc.
3. Remove ALL language specifications like: "to Spanish", "in English", "en français", "in zulu", etc.
4. Remove ALL instruction words like: "please", "can you", "could you", etc.
5. Keep ONLY the pure text content that should be translated.
6. If there are multiple sentences, keep all content sentences but remove command parts.
7. Preserve the original meaning and context of the main content.
8. If the input is already pure content without commands, return it as is.

Examples:
- Input: "translate hello world to Spanish" → Output: "hello world"
- Input: "good morning in japanese" → Output: "good morning"
- Input: "translate i live in bangladesh in zulu" → Output: "i live in bangladesh"
- Input: "I love programming in hawaiian" → Output: "I love programming"
- Input: "Bangladesh is a beautiful country" → Output: "Bangladesh is a beautiful country"
- Input: "অনুবাদ করুন hello world ইংরেজিতে" → Output: "hello world"
- Input: "how do you say thank you in german" → Output: "thank you"

Respond with ONLY the extracted text, nothing else. If no text to translate is found, respond with "NO_TEXT_FOUND".
"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a text extraction expert. Extract only the main content to translate, removing all commands and language specifications. Respond with only the extracted text."},
                    {"role": "user", "content": extraction_prompt}
                ],
                max_tokens=2048,
                temperature=0.1
            )
            extracted_text = response.choices[0].message.content.strip()
            if extracted_text == "NO_TEXT_FOUND" or not extracted_text:
                return self.fallback_text_extraction(user_input)
            if extracted_text.startswith('"') and extracted_text.endswith('"'):
                extracted_text = extracted_text[1:-1]
            if extracted_text.startswith("'") and extracted_text.endswith("'"):
                extracted_text = extracted_text[1:-1]
            return extracted_text.strip()
        except Exception:
            return self.fallback_text_extraction(user_input)

    def clean_trailing_language_phrase(self, text: str) -> str:
        patterns = [
            r'\s+(?:in|to|into)\s+[a-zA-Z\s]+$', 
            r'\s+[a-zA-Z\s]*ish\s*$'
        ]
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text.strip()

    def fallback_text_extraction(self, user_input: str) -> str:
        text = user_input.strip()
        patterns_to_remove_start = [
            r'^translate\s+in\s+\w+\s+', r'^translate\s+', r'^অনুবাদ\s+করুন\s+',
            r'^ترجم\s+', r'^traduire\s+', r'^traduzir\s+', r'^how\s+do\s+you\s+say\s+'
        ]
        for pattern in patterns_to_remove_start:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        patterns_to_remove_end = [
            r'\s+(?:in|to|into)\s+[a-zA-Z]+\s*$', 
            r'\s+(?:in|to|into)\s+[a-zA-Z]+\s+[a-zA-Z]+\s*$',
            r'\s+[a-zA-Z]*ish\s*$'
        ]
        for pattern in patterns_to_remove_end:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        instruction_words = ['please', 'can you', 'could you', 'would you', 'kindly']
        words = text.split()
        while words and words[0].lower() in instruction_words:
            words.pop(0)
        cleaned_text = ' '.join(words).strip()
        return cleaned_text if cleaned_text else user_input.strip()

    def detect_language(self, text: str) -> str:
        try:
            detection_text = text[:500] if len(text) > 500 else text
            url = f"https://translation.googleapis.com/language/translate/v2/detect?key={self.google_api_key}"
            data = {'q': detection_text}
            response = requests.post(url, data=data)
            if response.status_code == 200:
                result = response.json()
                detected_language = result['data']['detections'][0][0]['language']
                confidence = result['data']['detections'][0][0]['confidence']
                return detected_language if confidence > 0.3 and detected_language in self.supported_languages else 'auto'
            return 'auto'
        except Exception:
            return 'auto'

    def split_text_into_chunks(self, text: str, max_chars: int) -> List[str]:
        if len(text) <= max_chars:
            return [text]
        chunks = []
        current_chunk = ""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            if len(sentence) > max_chars:
                words = sentence.split()
                temp_sentence = ""
                for word in words:
                    if len(temp_sentence + word + " ") <= max_chars:
                        temp_sentence += word + " "
                    else:
                        if temp_sentence:
                            chunks.append(temp_sentence.strip())
                        temp_sentence = word + " "
                if temp_sentence:
                    if len(current_chunk + temp_sentence) <= max_chars:
                        current_chunk += temp_sentence
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = temp_sentence
            else:
                if len(current_chunk + sentence) <= max_chars:
                    current_chunk += sentence + " "
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + " "
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        return chunks

    def translate_text(self, text: str, target_language_code: str, source_language_code: str = 'auto') -> dict:
        try:
            if len(text) > self.max_translation_chars:
                text_chunks = self.split_text_into_chunks(text, self.max_translation_chars)
                translated_chunks = []
                source_language = None
                for chunk in text_chunks:
                    chunk_result = self._translate_single_chunk(chunk, target_language_code, source_language_code)
                    if not chunk_result['success']:
                        return chunk_result
                    translated_chunks.append(chunk_result['translated_text'])
                    if source_language is None:
                        source_language = chunk_result['source_language']
                full_translation = ' '.join(translated_chunks)
                return {
                    'success': True,
                    'translated_text': full_translation,
                    'source_language': source_language,
                    'target_language': self.supported_languages.get(target_language_code, target_language_code),
                    'source_lang_code': chunk_result['source_lang_code'],
                    'target_lang_code': target_language_code,
                    'chunked': True,
                    'chunk_count': len(text_chunks)
                }
            else:
                result = self._translate_single_chunk(text, target_language_code, source_language_code)
                if result['success']:
                    result['chunked'] = False
                    result['chunk_count'] = 1
                return result
        except Exception as e:
            return {
                'success': False,
                'error': f"Translation failed: {str(e)}",
                'translated_text': None,
                'source_language': None,
                'target_language': None
            }

    def _translate_single_chunk(self, text: str, target_language_code: str, source_language_code: str = 'auto') -> dict:
        try:
            url = f"https://translation.googleapis.com/language/translate/v2?key={self.google_api_key}"
            data = {
                'q': text,
                'target': target_language_code,
                'format': 'text'
            }
            if source_language_code != 'auto':
                data['source'] = source_language_code
            response = requests.post(url, data=data)
            if response.status_code == 200:
                result = response.json()
                translated_text = result['data']['translations'][0]['translatedText']
                detected_source = result['data']['translations'][0].get('detectedSourceLanguage', source_language_code if source_language_code != 'auto' else 'en')
                return {
                    'success': True,
                    'translated_text': translated_text,
                    'source_language': self.supported_languages.get(detected_source, detected_source),
                    'target_language': self.supported_languages.get(target_language_code, target_language_code),
                    'source_lang_code': detected_source,
                    'target_lang_code': target_language_code
                }
            return {
                'success': False,
                'error': f"Translation API failed: {response.status_code}",
                'translated_text': None,
                'source_language': None,
                'target_language': None
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Translation failed: {str(e)}",
                'translated_text': None,
                'source_language': None,
                'target_language': None
            }

    def parse_with_ai(self, user_input: str) -> Dict:
        parsing_input = user_input[:self.openai_input_limit] + "..." if len(user_input) > self.openai_input_limit else user_input
        language_list = ", ".join([f"{name}={code}" for code, name in sorted(self.supported_languages.items(), key=lambda x: x[1])])
        prompt = f"""You are a translation request parser. Analyze the user input and determine if it's a translation request and what the target language should be.

User Input: "{parsing_input}"

Available Languages: {language_list[:2000]}...

Instructions:
1. Determine if this is a translation request.
2. Identify the target language.
3. Handle typos in language names.
4. Support all Google Translate languages.

Examples:
- "I live in Bangladesh in Zulu" → is_translation_request: true, target: Zulu (zu)
- "hello world in Hawaiian" → is_translation_request: true, target: Hawaiian (haw)
- "translate hello to Yoruba" → is_translation_request: true, target: Yoruba (yo)
- "I live in Bangladesh" → is_translation_request: false

Respond in JSON:
{{
    "is_translation_request": true/false,
    "target_language_code": "language code or null",
    "target_language_name": "full language name or null",
    "confidence": 0.0-1.0
}}"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a translation request parser. Always respond in valid JSON format only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_openai_tokens,
                temperature=0.1
            )
            ai_response = response.choices[0].message.content.strip()
            if ai_response.startswith('```json'):
                ai_response = ai_response[7:-3]
            result = json.loads(ai_response.strip())
            if result.get('is_translation_request', False):
                target_code = result.get('target_language_code', '').lower().strip()
                if target_code and target_code in self.supported_languages:
                    target_language_name = self.supported_languages[target_code]
                    extracted_text = self.smart_text_extraction(user_input, target_language_name)
                    if extracted_text and extracted_text.strip():
                        return {
                            'is_translation_request': True,
                            'text': extracted_text,
                            'target_language_code': target_code,
                            'target_language_name': target_language_name,
                            'confidence': result.get('confidence', 0.8)
                        }
                target_name = result.get('target_language_name', '').lower().strip()
                for code, name in self.supported_languages.items():
                    if target_name and (target_name in name.lower() or name.lower().startswith(target_name)):
                        extracted_text = self.smart_text_extraction(user_input, name)
                        if extracted_text and extracted_text.strip():
                            return {
                                'is_translation_request': True,
                                'text': extracted_text,
                                'target_language_code': code,
                                'target_language_name': name,
                                'confidence': result.get('confidence', 0.7)
                            }
            return {
                'is_translation_request': False,
                'text': None,
                'target_language_code': None,
                'target_language_name': None,
                'confidence': result.get('confidence', 0.5)
            }
        except Exception:
            return self.fallback_parse(user_input)

    def fallback_parse(self, user_input: str) -> Dict:
        user_input_lower = user_input.lower().strip()
        translation_keywords = ['translate', 'translat', 'traduir', 'অনুবাদ', 'ترجم', 'traduire', 'how do you say']
        implicit_patterns = [r'\s+in\s+[a-zA-Z\s]+']
        has_explicit_keyword = any(keyword in user_input_lower for keyword in translation_keywords)
        has_implicit_pattern = any(re.search(pattern, user_input_lower) for pattern in implicit_patterns)
        if not has_explicit_keyword and not has_implicit_pattern:
            return {
                'is_translation_request': False,
                'text': None,
                'target_language_code': None,
                'target_language_name': None,
                'confidence': 0.8
            }
        implicit_match = re.search(r'^(.+?)\s+in\s+([a-zA-Z\s]+)', user_input_lower)
        lang_mapping = {
            'spanish': 'es', 'span ish': 'es', 'spansh': 'es', 'english': 'en', 'engl ish': 'en', 'englsh': 'en',
            'french': 'fr', 'fren ch': 'fr', 'frnch': 'fr', 'german': 'de', 'germ an': 'de', 'germn': 'de',
            'italian': 'it', 'ital ian': 'it', 'portuguese': 'pt', 'port uguese': 'pt', 'russian': 'ru',
            'russ ian': 'ru', 'chinese': 'zh', 'chin ese': 'zh', 'japanese': 'ja', 'japan ese': 'ja', 'japan': 'ja',
            'korean': 'ko', 'kor ean': 'ko', 'arabic': 'ar', 'arab ic': 'ar', 'hindi': 'hi', 'hind i': 'hi',
            'bengali': 'bn', 'beng ali': 'bn', 'dutch': 'nl', 'du tch': 'nl', 'swedish': 'sv', 'swed ish': 'sv',
            'norwegian': 'no', 'norw egian': 'no', 'urdu': 'ur', 'ur du': 'ur', 'tamil': 'ta', 'tam il': 'ta',
            'telugu': 'te', 'tel ugu': 'te', 'creole': 'ht', 'haitian creole': 'ht', 'haitian': 'ht', 'zulu': 'zu',
            'zu lu': 'zu', 'yoruba': 'yo', 'yor uba': 'yo', 'swahili': 'sw', 'swah ili': 'sw', 'hawaiian': 'haw',
            'hawai ian': 'haw', 'esperanto': 'eo', 'esper anto': 'eo', 'afrikaans': 'af', 'afrik aans': 'af',
            'albanian': 'sq', 'alban ian': 'sq', 'amharic': 'am', 'amhar ic': 'am', 'armenian': 'hy',
            'armen ian': 'hy', 'azerbaijani': 'az', 'azerbaij ani': 'az', 'basque': 'eu', 'bas que': 'eu',
            'belarusian': 'be', 'belaru sian': 'be', 'bosnian': 'bs', 'bosn ian': 'bs', 'bulgarian': 'bg',
            'bulgar ian': 'bg', 'catalan': 'ca', 'catal an': 'ca', 'cebuano': 'ceb', 'cebu ano': 'ceb',
            'croatian': 'hr', 'croat ian': 'hr', 'czech': 'cs', 'cz ech': 'cs', 'danish': 'da', 'dan ish': 'da',
            'estonian': 'et', 'eston ian': 'et', 'filipino': 'tl', 'filip ino': 'tl', 'finnish': 'fi',
            'finn ish': 'fi', 'georgian': 'ka', 'georg ian': 'ka', 'greek': 'el', 'gre ek': 'el',
            'gujarati': 'gu', 'gujar ati': 'gu', 'hausa': 'ha', 'haus a': 'ha', 'hebrew': 'he', 'hebr ew': 'he',
            'hungarian': 'hu', 'hungar ian': 'hu', 'icelandic': 'is', 'icel andic': 'is', 'igbo': 'ig',
            'ig bo': 'ig', 'indonesian': 'id', 'indones ian': 'id', 'irish': 'ga', 'ir ish': 'ga',
            'javanese': 'jw', 'javan ese': 'jw', 'kannada': 'kn', 'kann ada': 'kn', 'kazakh': 'kk',
            'kaz akh': 'kk', 'khmer': 'km', 'khm er': 'km', 'kurdish': 'ku', 'kurd ish': 'ku', 'kyrgyz': 'ky',
            'kyrg yz': 'ky', 'lao': 'lo', 'la o': 'lo', 'latin': 'la', 'lat in': 'la', 'latvian': 'lv',
            'latv ian': 'lv', 'lithuanian': 'lt', 'lithuan ian': 'lt', 'luxembourgish': 'lb',
            'luxemb ourgish': 'lb', 'macedonian': 'mk', 'macedon ian': 'mk', 'malagasy': 'mg',
            'malag asy': 'mg', 'malay': 'ms', 'mal ay': 'ms', 'malayalam': 'ml', 'malaya lam': 'ml',
            'maltese': 'mt', 'malt ese': 'mt', 'maori': 'mi', 'mao ri': 'mi', 'marathi': 'mr',
            'marath i': 'mr', 'mongolian': 'mn', 'mongol ian': 'mn', 'myanmar': 'my', 'myan mar': 'my',
            'burmese': 'my', 'nepali': 'ne', 'nep ali': 'ne', 'persian': 'fa', 'pers ian': 'fa',
            'polish': 'pl', 'pol ish': 'pl', 'punjabi': 'pa', 'punj abi': 'pa', 'romanian': 'ro',
            'roman ian': 'ro', 'samoan': 'sm', 'samo an': 'sm', 'sanskrit': 'sa', 'sanskr it': 'sa',
            'serbian': 'sr', 'serb ian': 'sr', 'sinhala': 'si', 'sinh ala': 'si', 'slovak': 'sk',
            'slov ak': 'sk', 'slovenian': 'sl', 'sloven ian': 'sl', 'somali': 'so', 'som ali': 'so',
            'sundanese': 'su', 'sundan ese': 'su', 'tajik': 'tg', 'taj ik': 'tg', 'tatar': 'tt',
            'tat ar': 'tt', 'thai': 'th', 'th ai': 'th', 'turkish': 'tr', 'turk ish': 'tr',
            'turkmen': 'tk', 'turkm en': 'tk', 'ukrainian': 'uk', 'ukrain ian': 'uk', 'uyghur': 'ug',
            'uygh ur': 'ug', 'uzbek': 'uz', 'uzb ek': 'uz', 'vietnamese': 'vi', 'vietnam ese': 'vi',
            'welsh': 'cy', 'wel sh': 'cy', 'xhosa': 'xh', 'xhos a': 'xh', 'yiddish': 'yi', 'yidd ish': 'yi'
        }
        if implicit_match:
            text_part = implicit_match.group(1).strip()
            lang_part = implicit_match.group(2).strip()
            lang_key = lang_part.replace(' ', '')
            target_code = lang_mapping.get(lang_key) or lang_mapping.get(lang_part)
            if not target_code:
                for code, name in self.supported_languages.items():
                    if lang_key and (lang_key in name.lower().replace(' ', '') or name.lower().replace(' ', '').startswith(lang_key[:4])):
                        target_code = code
                        break
                    if lang_part and (lang_part in name.lower() or name.lower().startswith(lang_part[:4])):
                        target_code = code
                        break
            if target_code and target_code in self.supported_languages:
                extracted_text = text_part.strip()
                return {
                    'is_translation_request': True,
                    'text': extracted_text,
                    'target_language_code': target_code,
                    'target_language_name': self.supported_languages[target_code],
                    'confidence': 0.9
                }
        explicit_match = re.search(r'^(.*?)(?:\s+(?:to|in|into)\s+([a-zA-Z ]+))', user_input_lower)
        if explicit_match and any(keyword in explicit_match.group(1) for keyword in translation_keywords):
            text_part = explicit_match.group(1).strip()
            lang_part = explicit_match.group(2).strip() if explicit_match.group(2) else None
            lang_key = lang_part.replace(' ', '') if lang_part else ''
            target_code = lang_mapping.get(lang_key) or lang_mapping.get(lang_part)
            if not target_code:
                for code, name in self.supported_languages.items():
                    if lang_key and (lang_key in name.lower().replace(' ', '') or name.lower().replace(' ', '').startswith(lang_key[:4])):
                        target_code = code
                        break
                    if lang_part and (lang_part in name.lower() or name.lower().startswith(lang_part[:4])):
                        target_code = code
                        break
            if target_code and target_code in self.supported_languages:
                extracted_text = self.smart_text_extraction(text_part, self.supported_languages[target_code])
                if not extracted_text or extracted_text.strip() == "":
                    extracted_text = self.fallback_text_extraction(text_part)
                return {
                    'is_translation_request': True,
                    'text': extracted_text,
                    'target_language_code': target_code,
                    'target_language_name': self.supported_languages[target_code],
                    'confidence': 0.8
                }
        if has_explicit_keyword:
            # If user used a translation keyword but DID NOT specify a target language,
            # treat it as NOT a translation request so the system falls back to normal chat.
            # Only consider it a translation request if a target language is present.
            lang_match = re.search(r'(?:to|in|into)\s+([a-zA-Z\s]+)$', user_input_lower)
            if lang_match:
                lang_part = lang_match.group(1).strip()
                # try to resolve language
                lang_key = lang_part.replace(' ', '')
                target_code = None
                # check mapping shortcuts first
                target_code = lang_mapping.get(lang_key) or lang_mapping.get(lang_part)
                if not target_code:
                    for code, name in self.supported_languages.items():
                        if lang_key and (lang_key in name.lower().replace(' ', '') or name.lower().replace(' ', '').startswith(lang_key[:4])):
                            target_code = code
                            break
                        if lang_part and (lang_part in name.lower() or name.lower().startswith(lang_part[:4])):
                            target_code = code
                            break
                if target_code and target_code in self.supported_languages:
                    extracted_text = self.smart_text_extraction(user_input, self.supported_languages[target_code])
                    if not extracted_text or extracted_text.strip() == "":
                        extracted_text = self.fallback_text_extraction(user_input)
                    return {
                        'is_translation_request': True,
                        'text': extracted_text.strip(),
                        'target_language_code': target_code,
                        'target_language_name': self.supported_languages[target_code],
                        'confidence': 0.6
                    }
            # no valid target language found -> not a translation request
            return {
                'is_translation_request': False,
                'text': None,
                'target_language_code': None,
                'target_language_name': None,
                'confidence': 0.2
            }
        return {
            'is_translation_request': False,
            'text': None,
            'target_language_code': None,
            'target_language_name': None,
            'confidence': 0.3
        }

    def create_json_output(self, original_text: str, translated_text: str, source_language: str, target_language: str, source_code: str, target_code: str, success: bool = True, error: str = None) -> dict:
        return {
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "translation": {
                "given_text": original_text,
                "given_language": source_language,
                "given_language_code": source_code,
                "translated_text": translated_text,
                "translated_language": target_language,
                "translated_language_code": target_code
            },
            "error": error if not success else None
        }

    def sanitize_json_output(self, data: dict) -> dict:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        try:
            while (
                isinstance(out.get('translation'), dict)
                and 'translation' in out['translation']
                and isinstance(out['translation']['translation'], dict)
            ):
                inner = out['translation'].pop('translation')
                if 'timestamp' in inner and 'timestamp' not in out:
                    out['timestamp'] = inner.pop('timestamp')
                for k, v in inner.items():
                    if k not in out['translation']:
                        out['translation'][k] = v
            if isinstance(out.get('translation'), dict):
                if 'timestamp' in out['translation'] and 'timestamp' in out:
                    out['translation'].pop('timestamp', None)
        except Exception:
            return out
        return out

    def process_translation(self, text: str, target_language_code: str, target_language_name: str) -> dict:
        if not text or not text.strip():
            return self.create_json_output("", "", "", "", "", "", False, "No text provided to translate")
        clean_text = text.strip()
        translation_result = self.translate_text(clean_text, target_language_code)
        if translation_result['success']:
            source_lang = translation_result['source_language']
            target_lang = translation_result['target_language']
            source_code = translation_result['source_lang_code']
            original_text = clean_text
            translated_text = translation_result['translated_text']
            json_output = self.create_json_output(
                original_text, translated_text, source_lang, target_lang, source_code, target_language_code
            )
            if translation_result.get('chunked', False):
                json_output['translation']['chunked'] = True
                json_output['translation']['chunk_count'] = translation_result.get('chunk_count', 1)
            return self.sanitize_json_output(json_output)
        return self.create_json_output(clean_text, "", "Unknown", target_language_name, "auto", target_language_code, False, translation_result['error'])

    def get_supported_languages(self) -> List[Dict]:
        return [{"code": code, "name": name} for code, name in self.supported_languages.items()]