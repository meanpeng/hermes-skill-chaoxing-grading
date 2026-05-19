# Step 04: Materials

Read `references/agent-rules.md` first. Use this step only after the teacher has confirmed `concise` or `detailed` scoring. If the mode is `random`, skip this file.

## Already Downloaded Zip

Prefer the batch material-prep script when one or more zip files have been downloaded:

```bash
python scripts/prepare_work_materials.py \
  --zip-dir downloads/ai-principles \
  --output-dir prepared/ai-principles \
  --mode metrics \
  --sample 5
```

For a single file:

```bash
python scripts/prepare_work_materials.py \
  --zip-file "downloads/ai-principles/CLASS-ASSIGNMENT.zip" \
  --output-dir prepared/ai-principles \
  --mode metrics
```

The script extracts each zip into its own folder, expands nested student zips, runs material or metric analysis, writes per-assignment CSVs, writes an `agent_material_report.md` for each assignment, and writes `materials_manifest.csv/json`.

This step must not generate draft scores. It only reports extraction status, character count, image count, structure/section signals, reflection signal, and report paths for later agent or teacher judgment.

Manual equivalent:

```bash
python scripts/extract_work_zip.py output.zip -d output_dir
python scripts/batch_grade.py --base-dir output_dir --mode materials
```

For optional rough signals:

```bash
python scripts/batch_grade.py --base-dir output_dir --mode metrics
python scripts/batch_grade.py --base-dir output_dir --mode metrics --sample 5
```

Treat these fields as reading aids, not automatic grades:

- `status`: `ok`, `too_short`, `missing_report`, `unreadable`
- `char_count`
- `img_count`
- `format`
- `expanded_zip`
- `report_path`
- `preview`
- `section_signal`
- `reflection_signal`

## Agent-Side Unreadable Confirmation

Treat `status=unreadable` as a required direct inspection path for the agent, not as an immediate teacher-review item.

Before reporting an unreadable submission as unresolved:

1. Open the student's extracted folder and personally inspect available candidates: another `.docx`, `.doc`, nested zip, PDF, or original attachment.
2. If there are nested archives or attachments, inspect their contents directly with local tools rather than only relying on the material-prep CSV.
3. If a Word report is unreadable, try an appropriate local reader/extractor for that file type and inspect file size/content signals before deciding it is unresolved.
4. If the confirmed scoring mode permits material access, inspect an already downloaded PDF/original-attachment package for the same assignment, or safely obtain that alternate package using the dry-run-first download flow and inspect the relevant student's file.

Rerunning `prepare_work_materials.py` or `batch_grade.py` is not the confirmation step. Scripts can help locate or summarize files, but the confirmation must come from the agent's direct inspection of the student's candidate files.

Only after these direct inspection attempts fail should the final score draft list the student as requiring teacher review, and the reason must say which files or alternatives were inspected.

## Export From Chaoxing

Prefer the dry-run-first download script for repeated exports:

```bash
python scripts/download_work_zips.py \
  --cookie-file cx_cookies.txt \
  --course "人工智能原理" \
  --class-contains "闵" \
  --assignment-contains "实验五" \
  --format word
```

The command above only lists target assignments. After the teacher has confirmed `concise` or `detailed` scoring and the exact target list is correct, add `--confirm-download`:

```bash
python scripts/download_work_zips.py \
  --cookie-file cx_cookies.txt \
  --course "人工智能原理" \
  --class-contains "闵" \
  --assignment-contains "实验五" \
  --format word \
  --output-dir downloads/ai-principles \
  --confirm-download
```

Supported formats:

- `--format word`: report Word package (`onlyattachment=0`, `isPdf=0`)
- `--format pdf`: PDF package (`onlyattachment=1`, `isPdf=1`)
- `--format attachment`: original attachment package (`onlyattachment=1`, `isPdf=0`)

To download specific assignments, repeat `--work-id`:

```bash
python scripts/download_work_zips.py \
  --cookie-file cx_cookies.txt \
  --course "人工智能原理" \
  --class-contains "闵" \
  --work-id 53469238 \
  --work-id 53320650 \
  --format word \
  --confirm-download
```

The script triggers `packWork`, polls the download center, reuses existing matching packages unless `--force-pack` is set, and writes deterministic local filenames. It does not extract or parse the zip.

### Manual Fallback

On a work/review page, first collect hidden inputs because global variables can be missing:

```js
var params = Array.from(document.querySelectorAll("input[type=hidden]")).reduce((result, input) => {
  if (input.name) result[input.name] = input.value;
  return result;
}, {});
params;
```

Trigger packaging from a logged-in page:

```js
new Promise((resolve) => {
  $.ajax({
    type: "get",
    url: "/mooc2-ans/work/packWork",
    data: {
      courseid: params.courseid || params.courseId,
      clazzid: params.clazzid || params.clazzId || params.currentClassId,
      workid: params.workid || params.workId,
      type: 0,
      onlyattachment: "0",
      isPdf: "0",
      packtype: "1",
      customNameGroup: "",
      wordCustomFormat: "",
      personIds: "",
    },
    success: data => resolve(data),
    error: xhr => resolve({ error: xhr.status }),
  });
});
```

After about 15 seconds, inspect the download center and pick the newest `workzip` URL whose `fn=` filename matches the target assignment.

Download with cookies:

```bash
curl -L -b cx_cookies.txt -o output.zip "DOWNLOAD_URL" -H "User-Agent: Mozilla/5.0"
python scripts/extract_work_zip.py output.zip -d output_dir
```

## Reading Notes

- `.docx`: `batch_grade.py` reads paragraphs and table cells.
- `.doc`: text extraction is best-effort and image count is estimated.
- `too_short` means a readable report exists but is below `--min-chars`; it is not the same as `missing_report`.
- `unreadable` must be checked through direct agent-side file inspection before teacher-facing review.
- Do not grade image-heavy reports from text length alone.
