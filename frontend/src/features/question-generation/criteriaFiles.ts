export const MAX_CRITERIA_FILE_BYTES = 16 * 1024;
export const MAX_CRITERIA_CHARACTERS = 16_384;

const SUPPORTED_EXTENSIONS = new Set(['.txt', '.md', '.json']);

export function criteriaFileExtension(fileName: string): string {
  const dotIndex = fileName.lastIndexOf('.');
  return dotIndex < 0 ? '' : fileName.slice(dotIndex).toLowerCase();
}

function flattenJson(value: unknown, label = ''): string[] {
  if (typeof value === 'string') {
    return [label ? `${label}: ${value}` : value];
  }
  if (Array.isArray(value)) {
    return value.flatMap((item) => flattenJson(item, label));
  }
  if (value && typeof value === 'object') {
    return Object.entries(value).flatMap(([key, item]) =>
      flattenJson(item, label ? `${label}.${key}` : key),
    );
  }
  return [];
}

export async function readCriteriaFile(file: File): Promise<string> {
  const extension = criteriaFileExtension(file.name);
  if (!SUPPORTED_EXTENSIONS.has(extension)) {
    throw new Error('Choose a .txt, .md, or .json criteria file.');
  }
  if (file.size > MAX_CRITERIA_FILE_BYTES) {
    throw new Error('Criteria files must be 16 KB or smaller.');
  }

  const contents = await file.text();
  let extracted = contents;
  if (extension === '.json') {
    let parsed: unknown;
    try {
      parsed = JSON.parse(contents);
    } catch {
      throw new Error('The selected JSON file is not valid JSON.');
    }
    extracted = flattenJson(parsed).join('\n');
  }

  if (extracted.length > MAX_CRITERIA_CHARACTERS) {
    throw new Error('Extracted criteria must be 16,384 characters or fewer.');
  }
  return extracted;
}
