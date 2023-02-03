from rq import get_current_job
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import sys
import traceback

# Read a vtt file from the given path and return timestamps + text
def read_vtt(path):
    timestamps = []
    segments = []

    with open(path, 'r') as vttfile:
        current_segment = []
        for line in vttfile:
            if '-->' in line:
                if len(current_segment) > 0:
                    segments.append('\n'.join(current_segment).strip())
                timestamps += [line.strip()]
            if line == '\n':
                continue
            current_segment.append(line)

    return timestamps, segments

def write_vtt(path, texts, timestamps):
    with open(path, 'w') as vttfile_output:
        for timestamp, text in zip(timestamps, texts):
            vttfile_output.write(f'{timestamp}\n{text}\n\n')

# Load Helsinki-NLP translation models for a given language
def load_translation_models(lang):
    try:
        tokenizer = AutoTokenizer.from_pretrained(f'Helsinki-NLP/opus-mt-{lang}')
        model = AutoModelForSeq2SeqLM.from_pretrained(f'Helsinki-NLP/opus-mt-{lang}')
    except:
        traceback.print_exc()
        print('Could not load translation model.')
        print('Does Helsinki-NLP support this translation pair? -> ', lang)
        sys.exit(-1)

    return tokenizer, model

# Translate text input with the language pair in lang (<l1>-<l2>), e.g. lang='de-en'
# for German -> English
def translate_text(text, lang='de-en'):
    tokenizer, model = load_translation_models(lang)

    translated = model.generate(**tokenizer(text, return_tensors="pt", padding=True, max_length=512))
    output = [tokenizer.decode(t, skip_special_tokens=True, max_length=512) for t in translated]

    return ''.join(output)

# Loads a vtt file from path and translates the segments with the given language pair (e.g. lang='de-en')
def translate_vtt(input_path, output_path='', lang='de-en'):

    assert(input_path.endswith('.vtt'))
    timestamps, text_segments = read_vtt(input_path)
    print(len(timestamps), len(text_segments))
    assert(len(timestamps) == len(text_segments))
    text = ' ## '.join(text_segments)
    output = translate_text(text, lang)
    translated_segments =  output.split(' ## ')

    # if no output path is specificed we use a default one based on the input path
    # append _targetlang to the basepath of the input path 
    # e.g. test.vtt translated to English = test_en.vtt
    if output_path == '':
        target_language = lang.split('-')[1]
        basepath = input_path[:-4]
        output_path = f'{basepath}_{target_language}.vtt'

    write_vtt(output_path, translated_segments, timestamps)

if __name__ == '__main__':
    translate_vtt('transcripts/Neujahrsansprache.mp4.vtt', lang='de-en')    
