/**
 * An Excel workbook, built by the test.
 *
 * No library: an .xlsx is a zip of XML, and the suite needs one sheet of
 * strings, so a stored (uncompressed) zip of the five parts a reader requires
 * is enough, and adds nothing to the console's dependencies. What reads it is
 * the API's own `openpyxl`, so a file that is not a real workbook fails here.
 */
import { crc32 } from "node:zlib";

function zip(parts: Array<[string, string]>): Buffer {
  const u16 = (n: number) => {
    const b = Buffer.alloc(2);
    b.writeUInt16LE(n);
    return b;
  };
  const u32 = (n: number) => {
    const b = Buffer.alloc(4);
    b.writeUInt32LE(n >>> 0);
    return b;
  };
  const locals: Buffer[] = [];
  const centrals: Buffer[] = [];
  let at = 0;
  for (const [name, text] of parts) {
    const data = Buffer.from(text, "utf8");
    const path = Buffer.from(name, "utf8");
    // Version 2.0, UTF-8 names, stored; the time and date are left at zero.
    const common = Buffer.concat([
      u16(20),
      u16(0x0800),
      u16(0),
      u32(0),
      u32(crc32(data)),
      u32(data.length),
      u32(data.length),
      u16(path.length),
      u16(0),
    ]);
    const local = Buffer.concat([u32(0x04034b50), common, path, data]);
    centrals.push(
      Buffer.concat([u32(0x02014b50), u16(20), common, u16(0), u16(0), u16(0), u32(0), u32(at), path]),
    );
    locals.push(local);
    at += local.length;
  }
  const central = Buffer.concat(centrals);
  const end = Buffer.concat([
    u32(0x06054b50),
    u16(0),
    u16(0),
    u16(parts.length),
    u16(parts.length),
    u32(central.length),
    u32(at),
    u16(0),
  ]);
  return Buffer.concat([...locals, central, end]);
}

const escapeXml = (value: string) =>
  value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/** Column letters up to Z: a sheet here has three columns. */
const cell = (row: number, column: number, value: string) =>
  value === ""
    ? ""
    : `<c r="${String.fromCharCode(65 + column)}${row}" t="inlineStr"><is><t>${escapeXml(value)}</t></is></c>`;

/** One sheet of text: the first row is the headings. */
export function workbook(rows: string[][]): Buffer {
  const sheet = rows
    .map((values, i) => `<row r="${i + 1}">${values.map((v, j) => cell(i + 1, j, v)).join("")}</row>`)
    .join("");
  const xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n';
  const SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
  const REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
  return zip([
    [
      "[Content_Types].xml",
      `${xml}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">` +
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
        '<Default Extension="xml" ContentType="application/xml"/>' +
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' +
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' +
        "</Types>",
    ],
    [
      "_rels/.rels",
      `${xml}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
        `<Relationship Id="rId1" Type="${REL_NS}/officeDocument" Target="xl/workbook.xml"/>` +
        "</Relationships>",
    ],
    [
      "xl/workbook.xml",
      `${xml}<workbook xmlns="${SHEET_NS}" xmlns:r="${REL_NS}">` +
        '<sheets><sheet name="People" sheetId="1" r:id="rId1"/></sheets></workbook>',
    ],
    [
      "xl/_rels/workbook.xml.rels",
      `${xml}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
        `<Relationship Id="rId1" Type="${REL_NS}/worksheet" Target="worksheets/sheet1.xml"/>` +
        "</Relationships>",
    ],
    ["xl/worksheets/sheet1.xml", `${xml}<worksheet xmlns="${SHEET_NS}"><sheetData>${sheet}</sheetData></worksheet>`],
  ]);
}
