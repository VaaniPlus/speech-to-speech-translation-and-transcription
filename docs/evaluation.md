# Translation and transcription demo evaluation

[`data/evaluation/translation_transcription_demo.json`](../data/evaluation/translation_transcription_demo.json)
contains eight short, text-only example cases for English → Hindi and Hindi →
English. Each case provides source text, the expected transcript, and an
illustrative expected translation. The examples include short and longer
sentences, punctuation, numbers, and common fictional first names. They contain
no recordings, private user data, or personal data.

The expected outputs have been reviewed by a competent Hindi/English speaker
(`review_status` is `reviewed_by_competent_bilingual_speaker`). The dataset
contains no reviewer identity or other personal data.

For a manual regression check, use one case at a time: supply its source phrase
in the indicated direction, compare the recognized transcript with
`expected_transcript`, and compare the translated text with
`expected_translation`. Normalization such as numeral formatting may vary;
record observed differences instead of silently changing the expected text.
If speech input is needed, use a newly created, consented recording locally,
and do not add that recording to this dataset or repository.

This is a small illustrative demo set, not a scientific benchmark. It has no
statistical sampling, human-subject study, audio corpus, automated quality
score, or claim that a particular model is accurate. The automated test checks
dataset structure and coverage only; it does not validate linguistic
correctness.
