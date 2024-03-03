# Alfred
An AI ChatBot to use around the house. It's an LLM agent that can call
on tools to assist it.

# Plan
 - Re-implement using OpenAI assistants https://platform.openai.com/docs/assistants/how-it-works/creating-assistants
 - [ ] Replace TTS with Deepgram voice, does it sound better?
 - [ ] Improve dismissing
 - [ ] Improve latency
 - [ ] Try GPT-4?

# Design
Similar library: https://github.com/minimaxir/simpleaichat/tree/main
- [ ] Better SST and TTS tools: https://github.com/AlexandreSajus/JARVIS

## Multiple Prompts
First prompt just decides on tool, tried to handle both tool selection and response at once, but ChatGPT was too dumb.

## Tool Prompts
Tools need their own separate history, as otherwise  ChatGPT tends to refer to old messages rather than the 
current request.

## Speech to Text
 - Azure STT isn't bad but there's a lot of latency.
 - Whisper OpenAI? Doesn't look likely to be better
 - [Deepgram](https://deepgram.com/pricing)? They claim they're better, have speaker diarization. No good plan after free $200 are used up.

# Hardware
 - Kaysuda speakerphone didn't work well.
 - [eMeet Speakerphone](https://www.amazon.ca/dp/B07Q3D7F8S?psc=1&th=1&ascsubtag=7f99995271cb43d2b596ed6eec5045a7%7Cf98dbeec-b5cf-404b-bf62-ab48cdfda8d5%7Cdtp%7Ccn&linkCode=gg2&tag=cnet-buy-button-20)?

# Installation
 1. Download a service account key from [here](https://console.cloud.google.com/iam-admin/serviceaccounts/details/108424444541462896692/keys?project=jeeves-390215)
 2. Copy `env_example` to `.env` and fill in the relevant keys