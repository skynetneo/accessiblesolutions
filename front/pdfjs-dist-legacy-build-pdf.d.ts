declare module "pdfjs-dist/legacy/build/pdf.mjs" {
    export interface PdfJsTextContent {
        items: Array<{
            str?: string;
            transform?: number[];
        }>;
    }

    export interface PdfJsPage {
        getTextContent(): Promise<PdfJsTextContent>;
    }

    export interface PdfJsDocument {
        numPages: number;
        getPage(pageNumber: number): Promise<PdfJsPage>;
    }

    export function getDocument(options: {
        data: Uint8Array;
    }): {
        promise: Promise<PdfJsDocument>;
    };
}
