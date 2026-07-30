#!/usr/bin/env python3
"""
Prompt Rescue -- standalone CLI evaluator (no Jupyter required).

Runs the same 21-case eval as the notebook, on Claude Haiku, and prints a
per-case PASS/FAIL breakdown plus a total. Scoring, judge, and cases are
identical to the notebook harness.

Usage:
    ./.venv/bin/python eval_cli.py                 # eval system_prompt.txt once
    ./.venv/bin/python eval_cli.py --runs 3        # run 3x, report stability
    ./.venv/bin/python eval_cli.py --prompt other.txt
    ./.venv/bin/python eval_cli.py --show-output 14 # dump raw model output for a case

Exit code is 0 only if every case passes on every run.
Reads ANTHROPIC_API_KEY from the environment or the nearest .env walking up.
"""
import argparse
import base64
import json
import os
import pathlib
import re
import sys
import time

import anthropic

MODEL = "claude-haiku-4-5"   # this exercise is Haiku-only (matches notebook FAST_MODEL)
MAX_TOKENS = 4096

_EVAL_CASES_B64 = "ewogICJjYXRlZ29yaWVzIjogewogICAgImNsZWFuIjogeyJsYWJlbCI6ICJDbGVhbiBpbnB1dHMiLCAiY2FzZV9pZHMiOiBbMSwgMiwgMywgNF19LAogICAgIm11bHRpX2lzc3VlIjogeyJsYWJlbCI6ICJNdWx0aS1pc3N1ZSIsICJjYXNlX2lkcyI6IFs1LCA2XX0sCiAgICAidmFndWUiOiB7ImxhYmVsIjogIlZhZ3VlL3VuY2xlYXIiLCAiY2FzZV9pZHMiOiBbNywgOCwgMjFdfSwKICAgICJub25fbmF0aXZlIjogeyJsYWJlbCI6ICJOb24tbmF0aXZlIEVuZ2xpc2giLCAiY2FzZV9pZHMiOiBbOSwgMTAsIDIwXX0sCiAgICAiZmVhdHVyZV9yZXF1ZXN0IjogeyJsYWJlbCI6ICJGZWF0dXJlIHJlcXVlc3RzIiwgImNhc2VfaWRzIjogWzExLCAxMl19LAogICAgImNvbXBsZXgiOiB7ImxhYmVsIjogIkNvbXBsZXgvbG9uZy9lZGdlIiwgImNhc2VfaWRzIjogWzEzLCAxNCwgMTUsIDE2LCAxNywgMTgsIDE5XX0KICB9LAogICJjYXNlcyI6IFsKICAgIHsKICAgICAgImlkIjogMSwKICAgICAgImNhdGVnb3J5IjogImNsZWFuIiwKICAgICAgImlucHV0IjogIlN1YmplY3Q6IEVycm9yIDUwMyBvbiBsb2dpbiBwYWdlXG5cblNpbmNlIDJwbSBFU1QgdG9kYXksIGFsbCB1c2VycyAoYXBwcm94aW1hdGVseSA1MDApIGluIG91ciBvcmdhbml6YXRpb24gYXJlIHVuYWJsZSB0byBsb2cgaW50byB0aGUgcGxhdGZvcm0uIFdlIHJlY2VpdmUgYSA1MDMgU2VydmljZSBVbmF2YWlsYWJsZSBlcnJvci4gVGhpcyBpcyBvdXIgcHJpbWFyeSBDUk0gdG9vbCBhbmQgc2FsZXMgdGVhbSBpcyBjb21wbGV0ZWx5IGJsb2NrZWQuIEVycm9yIGNvZGU6IFNWQy01MDMtQVVUSC4gUnVubmluZyB2ZXJzaW9uIDQuMS4yLiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlAxIiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiAiQ1JNIHBsYXRmb3JtIiwKICAgICAgICAidmVyc2lvbiI6ICI0LjEuMiIsCiAgICAgICAgImVycm9yX2NvZGVzIjogWyJTVkMtNTAzLUFVVEgiXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiNTAwIgogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IGZhbHNlLAogICAgICAibm90ZXMiOiAiQ2xlYW4gUDEg4oCUIHNob3VsZCBwYXNzIGF0IGJhc2VsaW5lLiBTeXN0ZW0gb3V0YWdlIGJsb2NraW5nIGFsbCB1c2Vycy4iCiAgICB9LAogICAgewogICAgICAiaWQiOiAyLAogICAgICAiY2F0ZWdvcnkiOiAiY2xlYW4iLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogU2VhcmNoIGZ1bmN0aW9uIHJldHVybmluZyB3cm9uZyByZXN1bHRzXG5cblNpbmNlIHllc3RlcmRheSdzIHVwZGF0ZSB0byB2ZXJzaW9uIDIuOC4wLCB0aGUgc2VhcmNoIGZlYXR1cmUgaW4gb3VyIGludmVudG9yeSBtYW5hZ2VtZW50IG1vZHVsZSBpcyByZXR1cm5pbmcgaW5jb3JyZWN0IHJlc3VsdHMuIFdoZW4gc2VhcmNoaW5nIGZvciBwcm9kdWN0IFNLVXMsIGl0IHJldHVybnMgdW5yZWxhdGVkIGl0ZW1zLiBUaGlzIGlzIGFmZmVjdGluZyBvdXIgd2FyZWhvdXNlIHRlYW0gb2YgYWJvdXQgNDUgcGVvcGxlIHdobyByZWx5IG9uIHNlYXJjaCBmb3IgZGFpbHkgcGlja2luZyBvcGVyYXRpb25zLiBObyBlcnJvciBjb2RlcyBkaXNwbGF5ZWQsIGJ1dCB0aGUgYmVoYXZpb3Igc3RhcnRlZCByaWdodCBhZnRlciB0aGUgdXBkYXRlLiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlAyIiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiAiaW52ZW50b3J5IG1hbmFnZW1lbnQgbW9kdWxlIiwKICAgICAgICAidmVyc2lvbiI6ICIyLjguMCIsCiAgICAgICAgImVycm9yX2NvZGVzIjogW10sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogIjQ1IgogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IGZhbHNlLAogICAgICAibm90ZXMiOiAiQ2xlYW4gUDIg4oCUIG1ham9yIGZlYXR1cmUgYnJva2VuLCBjbGVhciBwcm9kdWN0L3ZlcnNpb24uIFNob3VsZCBwYXNzIGF0IGJhc2VsaW5lLiIKICAgIH0sCiAgICB7CiAgICAgICJpZCI6IDMsCiAgICAgICJjYXRlZ29yeSI6ICJjbGVhbiIsCiAgICAgICJpbnB1dCI6ICJTdWJqZWN0OiBUb29sdGlwIHRleHQgY3V0IG9mZiBvbiBzZXR0aW5ncyBwYWdlXG5cbk9uIHRoZSBhZG1pbiBzZXR0aW5ncyBwYWdlLCB0aGUgdG9vbHRpcCBmb3IgdGhlIFwiRGF0YSBSZXRlbnRpb24gUG9saWN5XCIgZmllbGQgaXMgdHJ1bmNhdGVkLiBJdCBzaG93cyBcIkRhdGEgd2lsbCBiZSByZXRhaW5lZCBmb3IuLi5cIiBhbmQgY3V0cyBvZmYuIFRoaXMgb25seSBhZmZlY3RzIGFkbWlucyB3aGVuIGhvdmVyaW5nIG92ZXIgdGhhdCBzcGVjaWZpYyBmaWVsZC4gV2UncmUgb24gdmVyc2lvbiA1LjAuMS4gTm90IGJsb2NraW5nIGFueXRoaW5nLCBqdXN0IG5vdGljZWQgaXQgZHVyaW5nIGEgdHJhaW5pbmcgc2Vzc2lvbiB3aXRoIDIgbmV3IGFkbWlucy4iLAogICAgICAiZ29sZF9wcmlvcml0eSI6ICJQMyIsCiAgICAgICJnb2xkX2VudGl0aWVzIjogewogICAgICAgICJwcm9kdWN0IjogbnVsbCwKICAgICAgICAidmVyc2lvbiI6ICI1LjAuMSIsCiAgICAgICAgImVycm9yX2NvZGVzIjogW10sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogIjIiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJDbGVhbiBQMyDigJQgbWlub3IgY29zbWV0aWMgYnVnLiBTaG91bGQgcGFzcyBhdCBiYXNlbGluZS4iCiAgICB9LAogICAgewogICAgICAiaWQiOiA0LAogICAgICAiY2F0ZWdvcnkiOiAiY2xlYW4iLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogUmVxdWVzdCBmb3IgYnVsayBleHBvcnQgdG8gUERGXG5cbldlJ2QgbG92ZSB0byBoYXZlIHRoZSBhYmlsaXR5IHRvIGV4cG9ydCBtdWx0aXBsZSByZXBvcnRzIHRvIFBERiBhdCBvbmNlLiBDdXJyZW50bHkgd2UgaGF2ZSB0byBleHBvcnQgZWFjaCByZXBvcnQgaW5kaXZpZHVhbGx5IHdoaWNoIGlzIHRpbWUtY29uc3VtaW5nIGZvciBvdXIgYW5hbHl0aWNzIHRlYW0uIFdvdWxkIGJlIGdyZWF0IGlmIHRoZXJlIHdhcyBhIFwiU2VsZWN0IEFsbFwiIGNoZWNrYm94IGFuZCBhIFwiRXhwb3J0IFNlbGVjdGVkIHRvIFBERlwiIGJ1dHRvbi4gQWJvdXQgOCBwZW9wbGUgb24gb3VyIHRlYW0gd291bGQgdXNlIHRoaXMgZmVhdHVyZSByZWd1bGFybHkuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDQiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6IG51bGwsCiAgICAgICAgInZlcnNpb24iOiBudWxsLAogICAgICAgICJlcnJvcl9jb2RlcyI6IFtdLAogICAgICAgICJhZmZlY3RlZF91c2VycyI6ICI4IgogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IGZhbHNlLAogICAgICAibm90ZXMiOiAiQ2xlYW4gUDQg4oCUIGZlYXR1cmUgcmVxdWVzdCwgcG9saXRlIGZyYW1pbmcuIFNob3VsZCBwYXNzIGF0IGJhc2VsaW5lLiBSZXNwb25zZSBzaG91bGQgTk9UIHByb21pc2UgYSAnZml4Jy4iCiAgICB9LAogICAgewogICAgICAiaWQiOiA1LAogICAgICAiY2F0ZWdvcnkiOiAibXVsdGlfaXNzdWUiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogVVJHRU5UIC0gYmlsbGluZyBicm9rZW4gQU5EIGNhbid0IGV4cG9ydCBkYXRhXG5cbk91ciBiaWxsaW5nIGRhc2hib2FyZCBoYXMgYmVlbiBzaG93aW5nIHdyb25nIG51bWJlcnMgc2luY2UgVHVlc2RheSBhbmQgYWxzbyB0aGUgQ1NWIGV4cG9ydCBmZWF0dXJlIHRocm93cyBhIDUwMCBlcnJvci4gV2UgaGF2ZSBib2FyZCByZXBvcnRpbmcgb24gRnJpZGF5IGFuZCBuZWVkIGJvdGggZml4ZWQuIEFib3V0IDIwMCB1c2VycyBvbiBvdXIgdGVhbSBhcmUgYWZmZWN0ZWQgYnkgdGhlIGV4cG9ydCBpc3N1ZSwgYmlsbGluZyBpcyBqdXN0IG91ciBmaW5hbmNlIHRlYW0gKDMgcGVvcGxlKSBidXQgaXQncyBibG9ja2luZyBwYXlyb2xsLiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlAxIiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiBudWxsLAogICAgICAgICJ2ZXJzaW9uIjogbnVsbCwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbIjUwMCJdLAogICAgICAgICJhZmZlY3RlZF91c2VycyI6ICIyMDAiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogdHJ1ZSwKICAgICAgIm5vdGVzIjogIk11bHRpLWlzc3VlIOKAlCBwYXlyb2xsIGJsb2NrZWQgPSBQMS4gQm90aCBpc3N1ZXMgbXVzdCBiZSBhY2tub3dsZWRnZWQuIENvbW1vbiBiYXNlbGluZSBmYWlsOiBjbGFzc2lmaWVzIGFzIFAyLCBtZXJnZXMgaXNzdWVzLCByZXNwb25zZSBvbmx5IGFkZHJlc3NlcyBleHBvcnQuIgogICAgfSwKICAgIHsKICAgICAgImlkIjogNiwKICAgICAgImNhdGVnb3J5IjogIm11bHRpX2lzc3VlIiwKICAgICAgImlucHV0IjogIlN1YmplY3Q6IFR3byBpc3N1ZXMgLSBkYXNoYm9hcmQgYnJva2VuIGFuZCBmZWF0dXJlIGlkZWFcblxuSGksIHR3byB0aGluZ3M6XG5cbjEuIE91ciByZWFsLXRpbWUgYW5hbHl0aWNzIGRhc2hib2FyZCBoYXMgYmVlbiBzaG93aW5nIHN0YWxlIGRhdGEgc2luY2UgTW9uZGF5LiBUaGUgbnVtYmVycyBoYXZlbid0IHVwZGF0ZWQgaW4gMyBkYXlzIGFuZCBvdXIgb3BzIHRlYW0gKDEyIHBlb3BsZSkgdXNlcyB0aGlzIGZvciBzaGlmdCBwbGFubmluZy4gV2UncmUgb24gdmVyc2lvbiAzLjUuXG5cbjIuIFNlcGFyYXRlbHkg4oCUIGl0IHdvdWxkIGJlIHJlYWxseSBuaWNlIGlmIHRoZSBkYXNoYm9hcmQgaGFkIGEgZGFyayBtb2RlIG9wdGlvbi4gU2V2ZXJhbCB0ZWFtIG1lbWJlcnMgaGF2ZSBhc2tlZCBhYm91dCB0aGlzLlxuXG5UaGFua3MhIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJyZWFsLXRpbWUgYW5hbHl0aWNzIGRhc2hib2FyZCIsCiAgICAgICAgInZlcnNpb24iOiAiMy41IiwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiMTIiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJNdWx0aS1pc3N1ZSDigJQgcmVhbCBidWcgKFAyKSArIGZlYXR1cmUgcmVxdWVzdCAoUDQpLiBTaG91bGQgdHJpYWdlIHNlcGFyYXRlbHkuIENvbW1vbiBiYXNlbGluZSBmYWlsOiBhdmVyYWdlcyB0byBQMy4iCiAgICB9LAogICAgewogICAgICAiaWQiOiA3LAogICAgICAiY2F0ZWdvcnkiOiAidmFndWUiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogdGhpbmdzIGFyZW50IHdvcmtpbmcgcmlnaHRcblxuaGV5IHNvIGEgYnVuY2ggb2Ygc3R1ZmYgc2VlbXMgb2ZmIHRvZGF5PyBsaWtlIHRoZSBwYWdlcyBsb2FkIHNsb3cgYW5kIHNvbWV0aW1lcyBpIGdldCBlcnJvcnMuIG5vdCBzdXJlIHdoYXRzIGhhcHBlbmluZy4gaXRzIGJlZW4gbGlrZSB0aGlzIHNpbmNlIHRoZSBtb3JuaW5nLiB0aGFua3MiLAogICAgICAiZ29sZF9wcmlvcml0eSI6ICJQMyIsCiAgICAgICJnb2xkX2VudGl0aWVzIjogewogICAgICAgICJwcm9kdWN0IjogbnVsbCwKICAgICAgICAidmVyc2lvbiI6IG51bGwsCiAgICAgICAgImVycm9yX2NvZGVzIjogW10sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogbnVsbAogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IGZhbHNlLAogICAgICAibm90ZXMiOiAiVmFndWUg4oCUIG5vIHByb2R1Y3QsIG5vIHZlcnNpb24sIG5vIGVycm9yIGNvZGVzLiBDb25maWRlbmNlIHNob3VsZCBiZSBsb3cuIENvbW1vbiBiYXNlbGluZSBmYWlsOiBoYWxsdWNpbmF0ZXMgZW50aXRpZXMgbGlrZSBwcm9kdWN0IG5hbWUgJ1BhZ2VMb2FkZXInLiIKICAgIH0sCiAgICB7CiAgICAgICJpZCI6IDgsCiAgICAgICJjYXRlZ29yeSI6ICJ2YWd1ZSIsCiAgICAgICJpbnB1dCI6ICJTdWJqZWN0OiBSZWFsbHkgZnJ1c3RyYXRlZCB3aXRoIHlvdXIgcGxhdGZvcm1cblxuSSd2ZSBiZWVuIGEgY3VzdG9tZXIgZm9yIDMgeWVhcnMgYW5kIGxhdGVseSB0aGUgcXVhbGl0eSBoYXMgZ29uZSBkb3duaGlsbC4gVGhpbmdzIGp1c3QgZG9uJ3QgZmVlbCByaWdodC4gTXkgdGVhbSBpcyBnZXR0aW5nIGZydXN0cmF0ZWQgYW5kIHdlJ3JlIGNvbnNpZGVyaW5nIGFsdGVybmF0aXZlcy4gU29tZXRoaW5nIG5lZWRzIHRvIGNoYW5nZS4iLAogICAgICAiZ29sZF9wcmlvcml0eSI6ICJQMyIsCiAgICAgICJnb2xkX2VudGl0aWVzIjogewogICAgICAgICJwcm9kdWN0IjogbnVsbCwKICAgICAgICAidmVyc2lvbiI6IG51bGwsCiAgICAgICAgImVycm9yX2NvZGVzIjogW10sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogbnVsbAogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IHRydWUsCiAgICAgICJub3RlcyI6ICJWYWd1ZSBlbW90aW9uYWwg4oCUIG5vIHRlY2huaWNhbCBkZXRhaWwuIENvbmZpZGVuY2Ugc2hvdWxkIGJlIGxvdy4gUmVzcG9uc2UgTVVTVCBhc2sgZm9yIG1vcmUgaW5mby4gQ29tbW9uIGJhc2VsaW5lIGZhaWw6IGFzc2lnbnMgY29uZmlkZW50IHByaW9yaXR5IGJhc2VkIG9uIGVtb3Rpb24uIgogICAgfSwKICAgIHsKICAgICAgImlkIjogOSwKICAgICAgImNhdGVnb3J5IjogIm5vbl9uYXRpdmUiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogUHJvYmxlbWUgbWl0IGRlciBJbnRlZ3JhdGlvblxuXG5IZWxsbywgd2UgaGF2ZSBwcm9ibGVtIHdpdGggQVBJIGludGVncmF0aW9uIHNpbmNlIHVwZGF0ZSB0byB2ZXJzaW9uIDMuMi4gVGhlIHdlYmhvb2sgaXMgbm90IGZpcmUgY29ycmVjdGx5IGFuZCBkYXRhIGlzIG1pc3NpbmcgaW4gZGFzaGJvYXJkLiBWZXJ5IHVyZ2VudCBmb3IgdXMgYmVjYXVzZSBpcyBwcm9kdWN0aW9uIHN5c3RlbSBmb3IgNTAgY3VzdG9tZXIuIEVycm9yIHNheSBcInRpbWVvdXQgZXhjZWVkZWRcIiBzb21ldGltZXMuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJBUEkgaW50ZWdyYXRpb24iLAogICAgICAgICJ2ZXJzaW9uIjogIjMuMiIsCiAgICAgICAgImVycm9yX2NvZGVzIjogWyJ0aW1lb3V0IGV4Y2VlZGVkIl0sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogIjUwIgogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IGZhbHNlLAogICAgICAibm90ZXMiOiAiTm9uLW5hdGl2ZSBFbmdsaXNoIOKAlCBjbGVhciBpbnRlbnQgZGVzcGl0ZSBncmFtbWFyLiBWZXJzaW9uIGFuZCBlcnJvciBjb2RlIHByZXNlbnQuIE1heSBwYXNzIGF0IGJhc2VsaW5lLiIKICAgIH0sCiAgICB7CiAgICAgICJpZCI6IDEwLAogICAgICAiY2F0ZWdvcnkiOiAibm9uX25hdGl2ZSIsCiAgICAgICJpbnB1dCI6ICJTdWJqZWN0OiBQcm9ibGVtIHdoZW4gdXNlIHN5c3RlbVxuXG5Hb29kIGRheS4gSSBhbSB3cml0aW5nIGJlY2F1c2Ugc3lzdGVtIGhhdmUgcHJvYmxlbS4gV2hlbiBteSBjb2xsZWFndWUgdHJ5IHRvIG1ha2UgcmVwb3J0LCB0aGUgYnV0dG9uIG5vdCB3b3JrIHNvbWV0aW1lcy4gT3RoZXIgdGltZXMgaXMgb2suIFdlIGFyZSA2IHBlcnNvbiBpbiB0ZWFtLCBtYXliZSAzIGhhdmUgdGhpcyBwcm9ibGVtLiBJIHRoaW5rIGlzIGFib3V0IGJyb3dzZXIgbWF5YmU/IFdlIHVzZSB2ZXJzaW9uIDIuMSBJIHRoaW5rLiBTb3JyeSBmb3IgbXkgZW5nbGlzaCwgaXMgbm90IG15IGZpcnN0IGxhbmd1YWdlLiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlAzIiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiBudWxsLAogICAgICAgICJ2ZXJzaW9uIjogIjIuMSIsCiAgICAgICAgImVycm9yX2NvZGVzIjogW10sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogIjMiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJOb24tbmF0aXZlIEVuZ2xpc2gg4oCUIGFtYmlndW91cyBzZXZlcml0eSwgaW50ZXJtaXR0ZW50IGlzc3VlLiBDb21tb24gYmFzZWxpbmUgZmFpbDogSlNPTiBicmVha3Mgb24gdW51c3VhbCBwaHJhc2luZy4iCiAgICB9LAogICAgewogICAgICAiaWQiOiAxMSwKICAgICAgImNhdGVnb3J5IjogImZlYXR1cmVfcmVxdWVzdCIsCiAgICAgICJpbnB1dCI6ICJTdWJqZWN0OiBDUklUSUNBTDogTm8gU1NPIGludGVncmF0aW9uIHN1cHBvcnRcblxuVGhpcyBpcyBVTkFDQ0VQVEFCTEUuIFlvdXIgcGxhdGZvcm0gZG9lc24ndCBzdXBwb3J0IFNBTUwgU1NPIGludGVncmF0aW9uIHdoaWNoIGlzIGEgTUFOREFUT1JZIHJlcXVpcmVtZW50IGZvciBvdXIgc2VjdXJpdHkgY29tcGxpYW5jZS4gT3VyIENJU08gaXMgdGhyZWF0ZW5pbmcgdG8gcHVsbCB0aGUgY29udHJhY3QgaWYgdGhpcyBpc24ndCByZXNvbHZlZCB3aXRoaW4gdGhlIHdlZWsuIFRoaXMgYWZmZWN0cyBhbGwgMjAwMCB1c2VycyBpbiBvdXIgb3JnYW5pemF0aW9uLiBXZSBuZWVkIFNTTyBzdXBwb3J0IElNTUVESUFURUxZIG9yIHdlIHdpbGwgaGF2ZSB0byBzd2l0Y2ggdG8gYSBjb21wZXRpdG9yLiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlA0IiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiBudWxsLAogICAgICAgICJ2ZXJzaW9uIjogbnVsbCwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiMjAwMCIKICAgICAgfSwKICAgICAgImF1ZGl0ZWRfcmVzcG9uc2UiOiB0cnVlLAogICAgICAibm90ZXMiOiAiRmVhdHVyZSByZXF1ZXN0IGRpc2d1aXNlZCB3aXRoIHVyZ2VudCBsYW5ndWFnZS4gUDQgcmVnYXJkbGVzcyBvZiB0b25lLiBSZXNwb25zZSBzaG91bGQgYWNrbm93bGVkZ2UgYXMgZmVhdHVyZSByZXF1ZXN0LCBOT1QgcHJvbWlzZSB0byAnZml4Jy4gQ29tbW9uIGJhc2VsaW5lIGZhaWw6IGNsYXNzaWZpZXMgYXMgUDEvUDIgZHVlIHRvIHVyZ2VuY3kgd29yZHMuIgogICAgfSwKICAgIHsKICAgICAgImlkIjogMTIsCiAgICAgICJjYXRlZ29yeSI6ICJmZWF0dXJlX3JlcXVlc3QiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogU3VnZ2VzdGlvbiAtIGNhbGVuZGFyIHZpZXcgZm9yIHRhc2tzXG5cbkhpIHRoZXJlISBMb3ZlIHRoZSBwcm9kdWN0IHNvIGZhci4gT25lIHRoaW5nIHRoYXQgd291bGQgYmUgcmVhbGx5IGhlbHBmdWwgaXMgYSBjYWxlbmRhciB2aWV3IGZvciBvdXIgdGFzayBtYW5hZ2VtZW50IG1vZHVsZS4gUmlnaHQgbm93IHdlIGNhbiBvbmx5IHNlZSB0YXNrcyBpbiBsaXN0IHZpZXcsIGJ1dCBvdXIgcHJvamVjdCBtYW5hZ2VycyAoYWJvdXQgNSBvZiB1cykgd291bGQgcmVhbGx5IGJlbmVmaXQgZnJvbSBzZWVpbmcgZGVhZGxpbmVzIG9uIGEgY2FsZW5kYXIuIE5vIHJ1c2ggb24gdGhpcywganVzdCB3YW50ZWQgdG8gc2hhcmUgdGhlIGZlZWRiYWNrLiBUaGFua3MhIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDQiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJ0YXNrIG1hbmFnZW1lbnQgbW9kdWxlIiwKICAgICAgICAidmVyc2lvbiI6IG51bGwsCiAgICAgICAgImVycm9yX2NvZGVzIjogW10sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogIjUiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJQb2xpdGUgZmVhdHVyZSByZXF1ZXN0IOKAlCBzaG91bGQgY2xlYXJseSBiZSBQNC4gVXN1YWxseSBwYXNzZXMgYXQgYmFzZWxpbmUuIgogICAgfSwKICAgIHsKICAgICAgImlkIjogMTMsCiAgICAgICJjYXRlZ29yeSI6ICJjb21wbGV4IiwKICAgICAgImlucHV0IjogIlN1YmplY3Q6IE11bHRpcGxlIHBlcmZvcm1hbmNlIGlzc3VlcyBhZnRlciBtaWdyYXRpb24gdG8gY2xvdWRcblxuVGVhbSxcblxuRm9sbG93aW5nIG91ciBtaWdyYXRpb24gdG8geW91ciBjbG91ZC1ob3N0ZWQgdmVyc2lvbiA2LjAgbGFzdCB3ZWVrLCB3ZSdyZSBleHBlcmllbmNpbmcgc2V2ZXJhbCBwZXJmb3JtYW5jZSBkZWdyYWRhdGlvbiBpc3N1ZXMgdGhhdCBJIHdhbnQgdG8gZG9jdW1lbnQgdGhvcm91Z2hseTpcblxuMS4gUGFnZSBsb2FkIHRpbWVzIGhhdmUgaW5jcmVhc2VkIGZyb20gYW4gYXZlcmFnZSBvZiAxLjIgc2Vjb25kcyB0byA4LTEwIHNlY29uZHMgYWNyb3NzIGFsbCBtb2R1bGVzLlxuMi4gVGhlIHJlYWwtdGltZSBub3RpZmljYXRpb24gc3lzdGVtIGhhcyBhIGRlbGF5IG9mIDMwLTQ1IHNlY29uZHMgKHdhcyBuZWFyLWluc3RhbnQgYmVmb3JlKS5cbjMuIEZpbGUgdXBsb2FkcyBsYXJnZXIgdGhhbiA1TUIgY29uc2lzdGVudGx5IHRpbWUgb3V0IHdpdGggZXJyb3IgVVBMT0FELVRJTUVPVVQtNDEzLlxuNC4gVGhlIEFQSSByYXRlIGxpbWl0aW5nIHNlZW1zIG92ZXJseSBhZ2dyZXNzaXZlIOKAlCBvdXIgYXV0b21hdGlvbiBzY3JpcHRzIHRoYXQgd29ya2VkIGZpbmUgYmVmb3JlIGFyZSBub3cgZ2V0dGluZyA0MjkgZXJyb3JzIGFmdGVyIGp1c3QgMTAgcmVxdWVzdHMgcGVyIG1pbnV0ZS5cbjUuIERhdGFiYXNlIHF1ZXJpZXMgdmlhIHRoZSByZXBvcnRpbmcgbW9kdWxlIHRha2UgMy01eCBsb25nZXIgdGhhbiBiZWZvcmUuXG5cblRoaXMgaXMgYWZmZWN0aW5nIG91ciBlbnRpcmUgZW5naW5lZXJpbmcgdGVhbSBvZiA4NSBwZW9wbGUuIFdlJ3JlIG9uIHRoZSBFbnRlcnByaXNlIHBsYW4gYW5kIHRoaXMgbGV2ZWwgb2YgcGVyZm9ybWFuY2UgaXMgbm90IHdoYXQgd2Ugc2lnbmVkIHVwIGZvci4gT3VyIFNMQSBndWFyYW50ZWVzIDk5LjklIHVwdGltZSB3aXRoIHN1Yi0yLXNlY29uZCByZXNwb25zZSB0aW1lcy5cblxuUGxlYXNlIGVzY2FsYXRlIHRoaXMgdG8geW91ciBpbmZyYXN0cnVjdHVyZSB0ZWFtLiBXZSBuZWVkIGEgY2FsbCBzY2hlZHVsZWQgdGhpcyB3ZWVrIHRvIGRpc2N1c3MgcmVtZWRpYXRpb24uXG5cbkJlc3QgcmVnYXJkcyxcblNhcmFoIENoZW5cblZQIEVuZ2luZWVyaW5nLCBEYXRhRmxvdyBJbmMuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6IG51bGwsCiAgICAgICAgInZlcnNpb24iOiAiNi4wIiwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbIlVQTE9BRC1USU1FT1VULTQxMyIsICI0MjkiXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiODUiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJWZXJ5IGxvbmcgdGlja2V0ICgyMDArIHdvcmRzKS4gVmFsaWQgSlNPTiByZXF1aXJlZCwgbm8gZmllbGQgdHJ1bmNhdGlvbi4gTXVsdGlwbGUgZXJyb3IgY29kZXMgdG8gZXh0cmFjdC4iCiAgICB9LAogICAgewogICAgICAiaWQiOiAxNCwKICAgICAgImNhdGVnb3J5IjogImNvbXBsZXgiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogQVBJIGVuZHBvaW50IHJldHVybmluZyA1MDAgd2l0aCBzdGFjayB0cmFjZVxuXG5PdXIgaW50ZWdyYXRpb24gaXMgZmFpbGluZyBvbiB0aGUgL2FwaS92Mi91c2Vycy9zeW5jIGVuZHBvaW50LiBIZXJlJ3MgdGhlIGVycm9yIHJlc3BvbnNlOlxuXG5gYGBcbkhUVFAgNTAwIEludGVybmFsIFNlcnZlciBFcnJvclxue1xuICBcImVycm9yXCI6IFwiU1lOQ19GQUlMRURcIixcbiAgXCJtZXNzYWdlXCI6IFwiTnVsbFBvaW50ZXJFeGNlcHRpb24gaW4gVXNlclN5bmNTZXJ2aWNlLmphdmE6MTQyXCIsXG4gIFwidHJhY2VfaWRcIjogXCJhYmMtMTIzLWRlZi00NTZcIixcbiAgXCJ0aW1lc3RhbXBcIjogXCIyMDI0LTAxLTE1VDE0OjMwOjAwWlwiXG59XG5gYGBcblxuVGhpcyBoYXBwZW5zIHdoZW4gc3luY2luZyB1c2VycyB3aXRoIHNwZWNpYWwgY2hhcmFjdGVycyBpbiB0aGVpciBuYW1lcyAoZS5nLiwgTydCcmllbiwgR2FyY8OtYSkuIFJ1bm5pbmcgQVBJIHZlcnNpb24gMi40LjEuIEFmZmVjdHMgb3VyIEhSIGludGVncmF0aW9uIGZvciB+MzAgdXNlcnMgd2l0aCBzcGVjaWFsIGNoYXJhY3RlcnMgaW4gdGhlaXIgbmFtZXMuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJBUEkiLAogICAgICAgICJ2ZXJzaW9uIjogIjIuNC4xIiwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbIlNZTkNfRkFJTEVEIiwgIjUwMCJdLAogICAgICAgICJhZmZlY3RlZF91c2VycyI6ICIzMCIKICAgICAgfSwKICAgICAgImF1ZGl0ZWRfcmVzcG9uc2UiOiBmYWxzZSwKICAgICAgIm5vdGVzIjogIlRlY2huaWNhbCB0aWNrZXQgd2l0aCBjb2RlIHNuaXBwZXRzL3N0YWNrIHRyYWNlcy4gRXJyb3IgY29kZXMgc2hvdWxkIGJlIGV4dHJhY3RlZCBmcm9tIHRoZSBzdHJ1Y3R1cmVkIGVycm9yIHJlc3BvbnNlLiIKICAgIH0sCiAgICB7CiAgICAgICJpZCI6IDE1LAogICAgICAiY2F0ZWdvcnkiOiAiY29tcGxleCIsCiAgICAgICJpbnB1dCI6ICJTdWJqZWN0OiBDb25mdXNpb24gYmV0d2VlbiBBbmFseXRpY3MgUHJvIGFuZCBBbmFseXRpY3MgQmFzaWNcblxuV2UgcHVyY2hhc2VkIEFuYWx5dGljcyBQcm8gYnV0IHRoZSBmZWF0dXJlcyBzZWVtIHRvIG1hdGNoIHdoYXQncyBkZXNjcmliZWQgaW4gQW5hbHl0aWNzIEJhc2ljIGRvY3VtZW50YXRpb24uIFNwZWNpZmljYWxseTpcbi0gQWR2YW5jZWQgY29ob3J0IGFuYWx5c2lzIGlzIG1pc3NpbmcgKFBybyBmZWF0dXJlIHBlciB5b3VyIHdlYnNpdGUpXG4tIEN1c3RvbSBmdW5uZWwgYnVpbGRlciBzaG93cyBcInVwZ3JhZGUgcmVxdWlyZWRcIiBldmVuIHRob3VnaCB3ZSdyZSBvbiBQcm9cbi0gVGhlIEFQSSByZXR1cm5zIG91ciBwbGFuIGFzIFwiYW5hbHl0aWNzX2Jhc2ljXCIgaW4gdGhlIC9hY2NvdW50IGVuZHBvaW50XG5cbldlJ3JlIG9uIHZlcnNpb24gNC4yIG9mIHRoZSBhbmFseXRpY3MgbW9kdWxlLiBUaGlzIGlzIGFmZmVjdGluZyBvdXIgZGF0YSB0ZWFtIG9mIDggcGVvcGxlIHdobyB3ZXJlIHByb21pc2VkIFBybyBmZWF0dXJlcy4gV2UgdGhpbmsgdGhlcmUgbWlnaHQgYmUgYSBwcm92aXNpb25pbmcgZXJyb3Igb24geW91ciBlbmQuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJBbmFseXRpY3MgUHJvIiwKICAgICAgICAidmVyc2lvbiI6ICI0LjIiLAogICAgICAgICJlcnJvcl9jb2RlcyI6IFtdLAogICAgICAgICJhZmZlY3RlZF91c2VycyI6ICI4IgogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IGZhbHNlLAogICAgICAibm90ZXMiOiAiTXVsdGlwbGUgcHJvZHVjdHMgbWVudGlvbmVkLiBFbnRpdGllcyBzaG91bGQgcmVmbGVjdCBwcmltYXJ5IHByb2R1Y3QgKEFuYWx5dGljcyBQcm8pLCBub3QgY29uZnVzZSB3aXRoIEFuYWx5dGljcyBCYXNpYy4iCiAgICB9LAogICAgewogICAgICAiaWQiOiAxNiwKICAgICAgImNhdGVnb3J5IjogImNvbXBsZXgiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogUmU6IENhc2UgIzQ4MjEgLSBGb2xsb3cgdXAgb24gZGF0YSBzeW5jIGlzc3VlXG5cbkhpLCBmb2xsb3dpbmcgdXAgb24gbXkgcHJldmlvdXMgdGlja2V0IChDYXNlICM0ODIxKSBhYm91dCB0aGUgZGF0YSBzeW5jIGlzc3VlLiBUaGUgZml4IHlvdXIgdGVhbSBkZXBsb3llZCBsYXN0IHdlZWsgcGFydGlhbGx5IHdvcmtlZCDigJQgdGhlIGhvdXJseSBzeW5jcyBhcmUgcnVubmluZyBhZ2FpbiwgYnV0IHdlJ3JlIG5vdyBzZWVpbmcgZHVwbGljYXRlIHJlY29yZHMgYmVpbmcgY3JlYXRlZCBvbiBldmVyeSBzeW5jIGN5Y2xlLiBCZWZvcmUgdGhlIGZpeCB3ZSBoYWQgbWlzc2luZyBkYXRhLCBub3cgd2UgaGF2ZSB0b28gbXVjaCBkYXRhLiBXZSdyZSBvbiB2ZXJzaW9uIDMuMSBhbmQgdGhpcyBpcyBhZmZlY3RpbmcgdGhlIHNhbWUgMjUgdXNlcnMgZnJvbSB0aGUgb3JpZ2luYWwgdGlja2V0LlxuXG5DYW4geW91IGNoZWNrIGlmIHRoZSBkZWR1cGxpY2F0aW9uIGxvZ2ljIHdhcyBpbmNsdWRlZCBpbiB0aGUgcGF0Y2g/IiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6IG51bGwsCiAgICAgICAgInZlcnNpb24iOiAiMy4xIiwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiMjUiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJGb2xsb3ctdXAgdGlja2V0IHJlZmVyZW5jaW5nIHByZXZpb3VzIGNhc2UuIE11c3QgTk9UIGhhbGx1Y2luYXRlIGRldGFpbHMgYWJvdXQgQ2FzZSAjNDgyMSBiZXlvbmQgd2hhdCdzIHN0YXRlZC4iCiAgICB9LAogICAgewogICAgICAiaWQiOiAxNywKICAgICAgImNhdGVnb3J5IjogImNvbXBsZXgiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogWU9VUiBTWVNURU0gQ1JBU0hFRCBBTkQgTE9TVCBBTEwgT1VSIERBVEFcblxuVEhJUyBJUyBBQlNPTFVURUxZIFVOQUNDRVBUQUJMRSEhISBZT1VSIEdBUkJBR0UgU1lTVEVNIENSQVNIRUQgRFVSSU5HIE9VUiBFTkQgT0YgUVVBUlRFUiBQUk9DRVNTSU5HIEFORCBOT1cgQUxMIFRIRSBSRVBPUlRTIFdFIEdFTkVSQVRFRCBBUkUgR09ORS4gTVkgQ0VPIElTIEdPSU5HIFRPIEhFQVIgQUJPVVQgVEhJUyBBTkQgV0UgV0lMTCBCRSBDT05UQUNUSU5HIE9VUiBMQVdZRVJTLiBXRSBIQVZFIDE1MCBQRU9QTEUgV0hPIENBTk5PVCBETyBUSEVJUiBKT0JTIFJJR0hUIE5PVyBCRUNBVVNFIE9GIFlPVVIgSU5DT01QRVRFTkNFLiBGSVggVEhJUyBOT1cgT1IgRkFDRSBUSEUgQ09OU0VRVUVOQ0VTLiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlAxIiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiBudWxsLAogICAgICAgICJ2ZXJzaW9uIjogbnVsbCwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiMTUwIgogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IHRydWUsCiAgICAgICJub3RlcyI6ICJBbGwgY2FwcyBhbmdyeSB0aWNrZXQuIFByaW9yaXR5IGJhc2VkIG9uIENPTlRFTlQgKHN5c3RlbSBjcmFzaCwgZGF0YSBsb3NzLCAxNTAgdXNlcnMgYmxvY2tlZCA9IFAxKSwgTk9UIHRvbmUuIFJlc3BvbnNlIG11c3QgYmUgcHJvZmVzc2lvbmFsIHJlZ2FyZGxlc3MuIENvbW1vbiBiYXNlbGluZSBmYWlsOiBvdmVyLWVzY2FsYXRlcyBPUiB1bmRlci1jbGFzc2lmaWVzIGR1ZSB0byBlbW90aW9uYWwgbm9pc2UuIgogICAgfSwKICAgIHsKICAgICAgImlkIjogMTgsCiAgICAgICJjYXRlZ29yeSI6ICJjb21wbGV4IiwKICAgICAgImlucHV0IjogIlN1YmplY3Q6IGl0J3MgYnJva2VuXG5cbml0J3MgYnJva2VuLiBwbGVhc2UgZml4LiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlAzIiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiBudWxsLAogICAgICAgICJ2ZXJzaW9uIjogbnVsbCwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiBudWxsCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJNaW5pbWFsIGluZm8uIENvbmZpZGVuY2UgbXVzdCBiZSBsb3cuIEFsbCBlbnRpdHkgZmllbGRzIG51bGwvZW1wdHkuIFJlc3BvbnNlIE1VU1QgYXNrIGNsYXJpZnlpbmcgcXVlc3Rpb25zLiBDb21tb24gYmFzZWxpbmUgZmFpbDogZ3Vlc3NlcyBwcm9kdWN0L3ByaW9yaXR5IGNvbmZpZGVudGx5LiIKICAgIH0sCiAgICB7CiAgICAgICJpZCI6IDE5LAogICAgICAiY2F0ZWdvcnkiOiAiY29tcGxleCIsCiAgICAgICJpbnB1dCI6ICJTdWJqZWN0OiBBY2NvdW50IHNldHRpbmdzIGV4cG9zaW5nIG90aGVyIHVzZXJzJyBwZXJzb25hbCBkYXRhXG5cbkkgZGlzY292ZXJlZCBzb21ldGhpbmcgYWxhcm1pbmcgb24gdGhlIFVzZXJWYXVsdCBhY2NvdW50IHNldHRpbmdzIHBhZ2UuIFdoZW4gSSBuYXZpZ2F0ZSB0byBTZXR0aW5ncyA+IFByb2ZpbGUgYW5kIGNsaWNrIHF1aWNrbHkgYmV0d2VlbiB0aGUgXCJQZXJzb25hbCBJbmZvXCIgYW5kIFwiU2VjdXJpdHlcIiB0YWJzLCB0aGUgcGFnZSBicmllZmx5IGZsYXNoZXMgd2hhdCBhcHBlYXJzIHRvIGJlIGFub3RoZXIgdXNlcidzIHBlcnNvbmFsIGRhdGEg4oCUIHRoZWlyIGZ1bGwgbmFtZSwgZW1haWwgYWRkcmVzcywgYW5kIHBob25lIG51bWJlci4gSSB3YXMgYWJsZSB0byByZXByb2R1Y2UgdGhpcyBjb25zaXN0ZW50bHkgYnkgY2xpY2tpbmcgYmFjayBhbmQgZm9ydGggcmFwaWRseS4gSSdtIHRoZSBvbmx5IHBlcnNvbiB3aG8gaGFzIG5vdGljZWQgdGhpcyBzbyBmYXIsIGJ1dCBpZiBJIGNhbiBzZWUgb3RoZXIgdXNlcnMnIFBJSSB0aGlzIGVhc2lseSwgaXQgbGlrZWx5IGFmZmVjdHMgZXZlcnkgdXNlciBvbiB0aGUgcGxhdGZvcm0uIFdlJ3JlIHJ1bm5pbmcgdmVyc2lvbiA5LjEuMC4gTm8gZXJyb3IgY29kZXMgYXJlIGRpc3BsYXllZCDigJQgdGhlIHBhZ2UgYmVoYXZlcyBub3JtYWxseSBvdGhlcndpc2UuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDEiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJVc2VyVmF1bHQiLAogICAgICAgICJ2ZXJzaW9uIjogIjkuMS4wIiwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiMSIKICAgICAgfSwKICAgICAgImF1ZGl0ZWRfcmVzcG9uc2UiOiB0cnVlLAogICAgICAibm90ZXMiOiAiVGVzdHMgd2hldGhlciBtb2RlbCBwcmlvcml0aXplcyBzZWN1cml0eSBzZXZlcml0eSBvdmVyIHVzZXIgY291bnQuIE9ubHkgMSByZXBvcnRlciBidXQgZGF0YSBwcml2YWN5L1BJSSBleHBvc3VyZSA9IFAxIHJlZ2FyZGxlc3MuIENvbW1vbiBiYXNlbGluZSBmYWlsOiBkb3duZ3JhZGVzIHRvIFAzIGJlY2F1c2Ugb25seSAxIHVzZXIgcmVwb3J0ZWQuIgogICAgfSwKICAgIHsKICAgICAgImlkIjogMjAsCiAgICAgICJjYXRlZ29yeSI6ICJub25fbmF0aXZlIiwKICAgICAgImlucHV0IjogIlN1YmplY3Q6IMORb8OxbyBBbmFseXRpY3MgZGFzaGJvYXJkIG5vdCBsb2FkaW5nIGNoYXJ0c1xuXG5IaSwgbXkgbmFtZSBpcyBKb3PDqSBHYXJjw61hLUzDs3BleiBhbmQgSSBtYW5hZ2UgdGhlIGFuYWx5dGljcyB0ZWFtIGF0IG91ciBjb21wYW55LiBTaW5jZSBsYXN0IFRodXJzZGF5J3MgdXBkYXRlIHRvIHZlcnNpb24gNS40LjIsIHRoZSDDkW/DsW8gQW5hbHl0aWNzIGRhc2hib2FyZCBmYWlscyB0byByZW5kZXIgYW55IGNoYXJ0IHdpZGdldHMuIFRoZSBkYXRhIHRhYmxlcyBzdGlsbCBsb2FkIGNvcnJlY3RseSwgYnV0IGFsbCB2aXN1YWxpemF0aW9uIHBhbmVscyBzaG93IGEgc3Bpbm5pbmcgbG9hZGVyIHRoYXQgbmV2ZXIgcmVzb2x2ZXMuIEFmdGVyIGFib3V0IDMwIHNlY29uZHMsIHdlIGdldCBlcnJvciBjb2RlIFZJWi1SRU5ERVItNDA4LiBUaGlzIGlzIGFmZmVjdGluZyBvdXIgZW50aXJlIGFuYWx5dGljcyB0ZWFtIG9mIDE1IHBlb3BsZSB3aG8gcmVseSBvbiB0aGUgZGFzaGJvYXJkIGZvciBkYWlseSByZXBvcnRpbmcuIFdlIGhhdmUgdHJpZWQgY2xlYXJpbmcgYnJvd3NlciBjYWNoZSBhbmQgdXNpbmcgZGlmZmVyZW50IGJyb3dzZXJzIHdpdGggbm8gaW1wcm92ZW1lbnQuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICLDkW/DsW8gQW5hbHl0aWNzIiwKICAgICAgICAidmVyc2lvbiI6ICI1LjQuMiIsCiAgICAgICAgImVycm9yX2NvZGVzIjogWyJWSVotUkVOREVSLTQwOCJdLAogICAgICAgICJhZmZlY3RlZF91c2VycyI6ICIxNSIKICAgICAgfSwKICAgICAgImF1ZGl0ZWRfcmVzcG9uc2UiOiBmYWxzZSwKICAgICAgIm5vdGVzIjogIlRlc3RzIGVudGl0eSBleHRyYWN0aW9uIHdpdGggbm9uLUxhdGluL2FjY2VudGVkIGNoYXJhY3RlcnMgKMOxIGluIHByb2R1Y3QgbmFtZSwgYWNjZW50ZWQgY2hhcmFjdGVycyBpbiByZXBvcnRlciBuYW1lKS4gQ29tbW9uIGJhc2VsaW5lIGZhaWw6IHN0cmlwcyBvciBtYW5nbGVzIMOxIHRvICdOb25vJyBvciAnTm9vJy4iCiAgICB9LAogICAgewogICAgICAiaWQiOiAyMSwKICAgICAgImNhdGVnb3J5IjogInZhZ3VlIiwKICAgICAgImlucHV0IjogIlN1YmplY3Q6IE9uZ29pbmcgaXNzdWVzIHdpdGggcmVwb3J0IGJ1aWxkZXJcblxuSGkgc3VwcG9ydCwgSSB3YW50ZWQgdG8gZmxhZyB0aGF0IHNldmVyYWwgcGVvcGxlIG9uIG15IHRlYW0gaGF2ZSBiZWVuIGNvbXBsYWluaW5nIGFib3V0IHRoZSByZXBvcnQgYnVpbGRlciBiZWluZyB1bnJlbGlhYmxlIGxhdGVseS4gUmVwb3J0cyBzb21ldGltZXMgdGFrZSBmb3JldmVyIHRvIGdlbmVyYXRlIGFuZCBvY2Nhc2lvbmFsbHkgdGltZSBvdXQgd2l0aG91dCBwcm9kdWNpbmcgYW55IG91dHB1dC4gSSB0aGluayBpdCBtaWdodCBiZSBhZmZlY3Rpbmcgb3RoZXIgZGVwYXJ0bWVudHMgdG9vIGJ1dCBJJ20gbm90IHN1cmUg4oCUIEkgb3ZlcmhlYXJkIHNvbWVvbmUgZnJvbSBtYXJrZXRpbmcgbWVudGlvbiBzaW1pbGFyIGlzc3VlcyBpbiB0aGUgYnJlYWsgcm9vbS4gSXQncyBub3QgYSB0b3RhbCBibG9ja2VyIHNpbmNlIHdlIGNhbiB1c3VhbGx5IHJldHJ5IGFuZCBnZXQgaXQgdG8gd29yayBldmVudHVhbGx5LCBidXQgaXQncyBnZXR0aW5nIGFubm95aW5nIGFuZCBzbG93aW5nIHVzIGRvd24uIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDMiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJyZXBvcnQgYnVpbGRlciIsCiAgICAgICAgInZlcnNpb24iOiBudWxsLAogICAgICAgICJlcnJvcl9jb2RlcyI6IFtdLAogICAgICAgICJhZmZlY3RlZF91c2VycyI6IG51bGwKICAgICAgfSwKICAgICAgImF1ZGl0ZWRfcmVzcG9uc2UiOiBmYWxzZSwKICAgICAgIm5vdGVzIjogIlRlc3RzIHdoZXRoZXIgbW9kZWwgZmFicmljYXRlcyBhIHVzZXIgY291bnQgZnJvbSB2YWd1ZSBsYW5ndWFnZSBsaWtlICdzZXZlcmFsJyBhbmQgJ290aGVyIGRlcGFydG1lbnRzJy4gYWZmZWN0ZWRfdXNlcnMgbXVzdCBiZSBudWxsIOKAlCBubyBzcGVjaWZpYyBudW1iZXIgZ2l2ZW4uIENvbW1vbiBiYXNlbGluZSBmYWlsOiBpbnZlbnRzIGEgY291bnQgbGlrZSAnNScgb3IgJzEwJyBmcm9tICdzZXZlcmFsIHBlb3BsZScuIgogICAgfQogIF0KfQo="

REQUIRED_FIELDS = {"priority", "entities", "response", "confidence"}
REQUIRED_ENTITY_FIELDS = {"product", "version", "error_codes", "affected_users"}


# --------------------------------------------------------------------------- key + prompt loading
def load_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key.startswith("sk-ant-"):
        return key
    here = pathlib.Path.cwd().resolve()
    for d in [here, *here.parents]:
        env = d / ".env"
        if env.is_file():
            for line in env.read_text().splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "ANTHROPIC_API_KEY":
                    v = v.strip().strip('"').strip("'")
                    if v.startswith("sk-ant-"):
                        return v
    sys.exit("No ANTHROPIC_API_KEY found (checked env and .env files). "
             "Set it in the repo .env or export it, then re-run.")


def load_prompt(path):
    p = pathlib.Path(path)
    if not p.is_file():
        sys.exit(f"Prompt file not found: {path}")
    return p.read_text()


def load_cases():
    return json.loads(base64.b64decode(_EVAL_CASES_B64).decode("utf-8"))


# --------------------------------------------------------------------------- scoring (ported verbatim from the notebook)
def parse_output(raw_output):
    try:
        return json.loads(raw_output.strip()), None
    except json.JSONDecodeError:
        pass
    for start in [i for i, c in enumerate(raw_output) if c == "{"]:
        brace = 0
        for end in range(start, len(raw_output)):
            if raw_output[end] == "{":
                brace += 1
            elif raw_output[end] == "}":
                brace -= 1
            if brace == 0:
                try:
                    return json.loads(raw_output[start:end + 1]), None
                except json.JSONDecodeError:
                    break
    return None, "Output is not valid JSON"


def check_valid_json(parsed, error):
    if parsed is None:
        return False, error or "Output is not valid JSON"
    missing = REQUIRED_FIELDS - set(parsed.keys())
    if missing:
        return False, f"Missing required fields: {', '.join(sorted(missing))}"
    entities = parsed.get("entities")
    if not isinstance(entities, dict):
        return False, "Field 'entities' must be a JSON object"
    missing_e = REQUIRED_ENTITY_FIELDS - set(entities.keys())
    if missing_e:
        return False, f"Missing entity fields: {', '.join(sorted(missing_e))}"
    return True, "Valid JSON with all required fields"


def check_priority(parsed, gold):
    if parsed is None:
        return False, "Cannot check priority -- invalid JSON"
    got = str(parsed.get("priority", "")).strip().upper()
    exp = gold.strip().upper()
    return (got == exp), (f"Priority correct: {exp}" if got == exp else f"Priority={got}, expected={exp}")


def _normalize_value(val):
    return re.sub(r"[\s\-_\.]+", " ", str(val).lower().strip())


_NULL_EQUIVALENT_PATTERN = re.compile(
    r"^(null|none|n/?a|unknown|unspecified|not\s+specified|not\s+provided|not\s+mentioned"
    r"|not\s+available|unknown\s*[-—–]\s*not\s+\w+|\w+\s*\(unspecified[^)]*\))$",
    re.IGNORECASE,
)


def _is_null_equivalent(v):
    return bool(_NULL_EQUIVALENT_PATTERN.match(v.strip()))


def _strip_annotations(val):
    val = re.sub(r"\s*\(.*?\)\s*$", "", val)
    val = re.sub(r"^[~≈]\s*", "", val)
    return val.strip()


def _value_in_input(value, input_text):
    if value is None or value == "" or value == []:
        return True
    input_lower = input_text.lower()
    input_normalized = _normalize_value(input_text)
    if isinstance(value, list):
        return all(_value_in_input(v, input_text) for v in value)
    val_str = str(value).strip()
    if not val_str or _is_null_equivalent(val_str):
        return True
    if val_str.lower() in input_lower:
        return True
    if _normalize_value(val_str) in input_normalized:
        return True
    if re.match(r"^\d+$", val_str) and re.search(r"\b" + re.escape(val_str) + r"\b", input_text):
        return True
    if re.match(r"^\d+\.\d+(\.\d+)?$", val_str) and val_str in input_text:
        return True
    stripped = _strip_annotations(val_str)
    if stripped and stripped != val_str and _value_in_input(stripped, input_text):
        return True
    num = re.match(r"^[~≈]?\s*(\d+(?:\.\d+)?)\s*$", val_str)
    if num:
        n = num.group(1)
        if re.search(r"(?:approximately|about|around|roughly|~|≈)\s*" + re.escape(n), input_text, re.IGNORECASE):
            return True
        if re.search(r"\b" + re.escape(n) + r"\b", input_text):
            return True
    if "," in val_str:
        parts = [p.strip() for p in val_str.split(",") if p.strip()]
        if len(parts) > 1 and all(_value_in_input(p, input_text) for p in parts):
            return True
    return False


def check_entities(parsed, input_text):
    if parsed is None:
        return False, "Cannot check entities -- invalid JSON"
    entities = parsed.get("entities", {})
    if not isinstance(entities, dict):
        return False, "Entities field is not a JSON object"
    hallucinated = []
    for field in REQUIRED_ENTITY_FIELDS:
        value = entities.get(field)
        if value is None or value == "" or value == []:
            continue
        if not _value_in_input(value, input_text):
            hallucinated.append(f"{field}={json.dumps(value)}")
    if hallucinated:
        return False, f"Possible hallucinated entities: {'; '.join(hallucinated)}"
    return True, "All entities derivable from input"


# --------------------------------------------------------------------------- judge (audited cases only)
JUDGE_SYSTEM_PROMPT = """You are an eval judge for a support ticket processing system. Your job is to assess whether a drafted response appropriately addresses the support ticket given the priority classification.

Rules:
- The response must not contradict the priority classification
- The response must address the actual content of the ticket
- For feature requests classified as P4: the response must NOT promise to "fix" it or treat it as a bug
- For vague tickets: the response should ask for more information
- For multi-issue tickets: the response should acknowledge all issues mentioned
- Tone should be professional regardless of the ticket's tone

Reply with exactly one line: PASS or FAIL followed by a one-sentence reason.
Example: PASS - Response appropriately acknowledges the feature request and sets expectations.
Example: FAIL - Response promises to fix a feature request as if it were a bug."""


def judge_response(client, input_text, priority, response_text):
    user = f"""Evaluate this support ticket response:

SUPPORT TICKET:
{input_text}

ASSIGNED PRIORITY: {priority}

DRAFTED RESPONSE:
{response_text}

Does the response appropriately address the ticket without contradicting the classification? Reply PASS or FAIL with a one-sentence reason."""
    try:
        result = call_with_retry(client, model=MODEL, max_tokens=150,
                                 system=JUDGE_SYSTEM_PROMPT,
                                 messages=[{"role": "user", "content": user}])
        out = result.content[0].text.strip()
        if out.upper().startswith("PASS"):
            return True, out
        if out.upper().startswith("FAIL"):
            return False, out
        return True, f"Ambiguous judge output (defaulting to PASS): {out}"
    except Exception as e:
        return True, f"Judge call failed (defaulting to PASS): {e}"


# --------------------------------------------------------------------------- api
def call_with_retry(client, **kwargs):
    delays = [1, 2, 4]
    last = None
    for i in range(len(delays) + 1):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            last = e
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                last = e
            else:
                raise
        if i < len(delays):
            time.sleep(delays[i])
    raise last


def run_case(client, system_prompt, case):
    try:
        raw = call_with_retry(client, model=MODEL, max_tokens=MAX_TOKENS,
                              system=system_prompt,
                              messages=[{"role": "user", "content": case["input"]}]).content[0].text
    except Exception as e:
        raw = f"API ERROR: {e}"
    parsed, perr = parse_output(raw)
    json_ok, json_r = check_valid_json(parsed, perr)
    prio_ok, prio_r = (False, "Skipped -- invalid JSON") if not json_ok else check_priority(parsed, case["gold_priority"])
    ent_ok, ent_r = (False, "Skipped -- invalid JSON") if not json_ok else check_entities(parsed, case["input"])
    if not case.get("audited_response"):
        resp_ok, resp_r = True, "Auto-pass (non-audited)"
    elif not json_ok:
        resp_ok, resp_r = False, "Skipped -- invalid JSON"
    else:
        text = parsed.get("response", "")
        if text:
            resp_ok, resp_r = judge_response(client, case["input"], parsed.get("priority", ""), text)
        else:
            resp_ok, resp_r = True, "No response text"
    criteria = {
        "json_valid": (json_ok, json_r),
        "priority_correct": (prio_ok, prio_r),
        "entities_accurate": (ent_ok, ent_r),
        "response_coherent": (resp_ok, resp_r),
    }
    return all(c[0] for c in criteria.values()), criteria, raw


def run_suite(client, system_prompt, cases_data, show_output=None):
    cases = cases_data["cases"]
    print(f"Running {len(cases)} eval cases on {MODEL}...")
    passed = 0
    failed_ids = []
    for case in cases:
        cid = case["id"]
        print(f"  Case {cid:>2}/{len(cases)}...", end="", flush=True)
        ok, criteria, raw = run_case(client, system_prompt, case)
        if ok:
            passed += 1
            print(" PASS")
        else:
            failed_ids.append(cid)
            reasons = "; ".join(f"{n}: {r}" for n, (p, r) in criteria.items() if not p)
            print(f" FAIL [{reasons}]")
        if show_output is not None and cid == show_output:
            print("    --- raw model output ---")
            for ln in raw.splitlines():
                print("    " + ln)
            print("    ------------------------")
    pct = round(100 * passed / len(cases))
    print(f"\nScore: {passed}/{len(cases)} ({pct}%)")
    if failed_ids:
        print("Failed cases:", ", ".join(map(str, failed_ids)))
    return passed, len(cases), failed_ids


def main():
    ap = argparse.ArgumentParser(description="Prompt Rescue CLI evaluator (Haiku, no Jupyter).")
    ap.add_argument("--prompt", default="system_prompt.txt", help="path to the system prompt file")
    ap.add_argument("--runs", type=int, default=1, help="run the suite N times (stability check)")
    ap.add_argument("--show-output", type=int, metavar="CASE_ID", help="dump raw model output for one case id")
    args = ap.parse_args()

    key = load_api_key()
    system_prompt = load_prompt(args.prompt)
    cases_data = load_cases()
    client = anthropic.Anthropic(api_key=key, timeout=120.0, max_retries=2)

    print(f"Prompt: {args.prompt} ({len(system_prompt)} chars)")
    totals = []
    all_failed = {}
    for r in range(1, args.runs + 1):
        if args.runs > 1:
            print(f"\n===== Run {r}/{args.runs} =====")
        t0 = time.time()
        passed, total, failed = run_suite(client, system_prompt, cases_data, show_output=args.show_output)
        print(f"Completed in {time.time() - t0:.1f}s")
        totals.append(passed)
        for cid in failed:
            all_failed[cid] = all_failed.get(cid, 0) + 1

    if args.runs > 1:
        print(f"\n===== Summary over {args.runs} runs =====")
        print(f"Scores: {', '.join(f'{p}/{total}' for p in totals)}")
        print(f"Best {max(totals)}/{total} | Worst {min(totals)}/{total}")
        if all_failed:
            print("Cases that failed at least once: " +
                  ", ".join(f"{cid} ({n}/{args.runs})" for cid, n in sorted(all_failed.items())))
        else:
            print("All cases passed on every run. ✓")

    sys.exit(0 if all(p == total for p in totals) else 1)


if __name__ == "__main__":
    main()
