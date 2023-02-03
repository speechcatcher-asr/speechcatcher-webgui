from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

lang = 'de-en'

def load_translation_models(lang):
    tokenizer = AutoTokenizer.from_pretrained(f'Helsinki-NLP/opus-mt-{lang}')
    model = AutoModelForSeq2SeqLM.from_pretrained(f'Helsinki-NLP/opus-mt-{lang}')
    return tokenizer, model

def translate(text, lang='de-en'):
    tokenizer, model = load_translation_models(lang)

    translated = model.generate(**tokenizer(text, return_tensors="pt", padding=True))
    output = [tokenizer.decode(t, skip_special_tokens=True) for t in translated]

    return ''.join(output)

text = '''Dieser Text ist nur ein Beispiel und es steht hier eigentlich nur Quatsch drin.
Irgendwas brauchen wir zum testen. Ich würde sagen,
dass wir noch ein paar mehr Segmente brauchen.
Eigentlich würde ich gerne aufhören zu schreiben,
aber um das hier wirklich gut zu testen brauchen wir 
noch ein wenig längeren Text.
Die Segmente sollen dann beim übersetzten nicht verloren gehen.
So das man die Übersetzung für Untertitel verwenden kann.'''.replace('\n',' ## ')

num_segments_text = len(text.split('##'))
output = translate(text, lang='de-en')
num_segments_output = len(output.split('##'))

print(text)
print(output)
print('setments input:', num_segments_text, 'segments translation:', num_segments_output)
