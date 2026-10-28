# 薇斯纳 (Vesna) voice lines
- File name = first 12 hex chars of sha1(text.strip().encode("utf-8")) + ".ogg" (strip leading/trailing whitespace; placeholders like {name} included as-is). voice_map.json keys are the exact original strings.
- Final audio: dlc/voice/<id>.ogg
- voice_map.json: {"<exact original text>": "<id>.ogg"}
- LINES.csv (UTF-8 BOM): text, file, source (file:list_name / json path)
- Sources: content.py, dlc/foods/world_and_prank.json, dlc/interactions/*.py.
  Left out as not spoken: DANIKA_VISITS (a different character), CODEX, TIER_INFO, GOOD, BAD, ITEMS, FOOD_REGIONS, COLORS, LEVELS, TIERS. Dict-valued text (e.g. TIER_WORDS) is not included yet.
- Pipeline (final, 657 files): GPT-SoVITS v2ProPlus zero-shot (refs cut from the Vesna corpus: lively clip for most lines, calm clip for LV/comfort/companion/late/back/sleep/yawn; seed 1234) -> RVC vesna-cn.pth (pitch 0, rmvpe, index_rate 0.75, protect 0.33) -> loudnorm I=-18 LUFS, 48 kHz mono Vorbis q5.
- Emoji are stripped from the text sent to TTS only; ids still hash the original text.
- Scripts on the PC: E:\AI\vesna_voice (start_api.bat, gen_batch.py, run_rvc.bat/rvc_batch.py, check.py).
- _samples/ = comparison clips (demo_B.mp3 raw GPT-SoVITS, demo_B_rvc.mp3 = chosen pipeline).
- 2026-10-16: +26 lines (greet_text x5, DANIKA_VISITS Vesna-speaker lines x21; Danika's lines excluded). Parenthetical stage directions like (小声) are stripped from TTS input too.
- 2026-10-16: redid 6 lines with stage directions (parentheticals stripped from TTS; '……(扭头)' voiced as '哼……'); +16 holiday lines (SOLAR, LUNAR, holiday_text National Day).
