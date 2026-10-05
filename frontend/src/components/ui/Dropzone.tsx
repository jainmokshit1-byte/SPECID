import { FileSpreadsheet, UploadCloud } from "lucide-react";
import { type DragEvent, useId, useRef, useState } from "react";

const MAX_MB = 50;
const OK = /\.(csv|txt|tsv|xlsx|xlsm)$/i;

/** Drop zone with a file picker (App Flow 5.2 step 2): checks extension and size before upload. */
export function Dropzone({
  onFile,
  file,
  label = "Drop a CSV or Excel file here",
  disabled,
  compact,
}: {
  onFile: (f: File) => void;
  file?: File | null;
  label?: string;
  disabled?: boolean;
  compact?: boolean;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function take(f: File | undefined) {
    if (!f) return;
    if (!OK.test(f.name)) return setError("Upload a .csv or .xlsx file.");
    if (f.size > MAX_MB * 1024 * 1024) return setError(`Files are limited to ${MAX_MB} MB.`);
    setError(null);
    onFile(f);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setOver(false);
    if (!disabled) take(e.dataTransfer.files[0]);
  }

  return (
    <div>
      <label
        htmlFor={id}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed text-center transition-colors ${
          compact ? "px-4 py-5" : "px-6 py-10"
        } ${
          over
            ? "border-primary bg-auto-bg"
            : "border-border-strong bg-surface hover:border-primary hover:bg-surface-2"
        } ${disabled ? "pointer-events-none opacity-50" : ""}`}
      >
        {file ? (
          <>
            <FileSpreadsheet
              size={compact ? 22 : 30}
              strokeWidth={1.5}
              aria-hidden="true"
              className="text-primary"
            />
            <span className="mt-2 font-mono text-mono text-text">{file.name}</span>
            <span className="text-label text-muted">
              {(file.size / 1024).toFixed(0)} KB · click or drop to change
            </span>
          </>
        ) : (
          <>
            <UploadCloud
              size={compact ? 22 : 30}
              strokeWidth={1.5}
              aria-hidden="true"
              className="text-primary"
            />
            <span className="mt-2 text-body font-medium text-text">{label}</span>
            <span className="text-label text-muted">or click to choose · up to {MAX_MB} MB</span>
          </>
        )}
        <input
          id={id}
          ref={input}
          type="file"
          accept=".csv,.txt,.tsv,.xlsx,.xlsm"
          className="sr-only"
          disabled={disabled}
          onChange={(e) => take(e.target.files?.[0])}
        />
      </label>
      {error && (
        <p role="alert" className="mt-2 text-label text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
