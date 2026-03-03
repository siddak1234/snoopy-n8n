"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MistralDocumentAi = void 0;
const n8n_workflow_1 = require("n8n-workflow");
class MistralDocumentAi {
    constructor() {
        this.description = {
            displayName: 'Mistral Document AI',
            name: 'mistralDocumentAi',
            icon: 'file:mistral.svg',
            group: ['transform'],
            version: 1,
            subtitle: '={{$parameter["model"]}}',
            description: 'Run Mistral OCR with binary PDF/image input',
            defaults: {
                name: 'Mistral Document AI',
            },
            inputs: ['main'],
            outputs: ['main'],
            credentials: [
                {
                    name: 'mistralCloudApi',
                    required: true,
                },
            ],
            properties: [
                {
                    displayName: 'Binary Property Name',
                    name: 'binaryPropertyName',
                    type: 'string',
                    default: 'data',
                    required: true,
                },
                {
                    displayName: 'Input Document Type',
                    name: 'inputDocumentType',
                    type: 'options',
                    default: 'auto',
                    options: [
                        { name: 'Auto', value: 'auto' },
                        { name: 'PDF', value: 'pdf' },
                        { name: 'Image', value: 'image' },
                    ],
                },
                {
                    displayName: 'Model',
                    name: 'model',
                    type: 'options',
                    default: 'mistral-ocr-latest',
                    options: [
                        { name: 'mistral-ocr-latest', value: 'mistral-ocr-latest' },
                    ],
                },
                {
                    displayName: 'Use Custom Model',
                    name: 'useCustomModel',
                    type: 'boolean',
                    default: false,
                },
                {
                    displayName: 'Custom Model',
                    name: 'customModel',
                    type: 'string',
                    default: '',
                    displayOptions: {
                        show: {
                            useCustomModel: [true],
                        },
                    },
                },
                {
                    displayName: 'Pages',
                    name: 'pages',
                    type: 'string',
                    default: '',
                    placeholder: '1-4,8,11-13',
                    description: 'Optional page range list. Sent to API and also applied client-side after response',
                },
                {
                    displayName: 'Extract Tables',
                    name: 'extractTables',
                    type: 'options',
                    default: 'inline',
                    options: [
                        { name: 'Inline', value: 'inline' },
                        { name: 'Markdown', value: 'markdown' },
                        { name: 'HTML', value: 'html' },
                    ],
                    description: 'Inline maps to table_format=null',
                },
                {
                    displayName: 'Extract Header',
                    name: 'extractHeader',
                    type: 'boolean',
                    default: false,
                },
                {
                    displayName: 'Extract Footer',
                    name: 'extractFooter',
                    type: 'boolean',
                    default: false,
                },
                {
                    displayName: 'Extract Images',
                    name: 'extractImages',
                    type: 'boolean',
                    default: false,
                },
                {
                    displayName: 'Image Limit',
                    name: 'imageLimit',
                    type: 'number',
                    typeOptions: { minValue: 1 },
                    default: 10,
                    displayOptions: {
                        show: {
                            extractImages: [true],
                        },
                    },
                },
                {
                    displayName: 'Min Image Size',
                    name: 'minImageSize',
                    type: 'number',
                    typeOptions: { minValue: 1 },
                    default: 0,
                    displayOptions: {
                        show: {
                            extractImages: [true],
                        },
                    },
                },
                {
                    displayName: 'Extract Hyperlinks',
                    name: 'extractHyperlinks',
                    type: 'boolean',
                    default: false,
                    description: 'Sent as pass-through if API supports it',
                },
                {
                    displayName: 'Enable Document Annotation',
                    name: 'enableDocumentAnnotation',
                    type: 'boolean',
                    default: false,
                },
                {
                    displayName: 'Annotate Per Page',
                    name: 'perPageAnnotation',
                    type: 'boolean',
                    default: false,
                    description: 'When enabled, processes each requested page separately and outputs one item per page',
                },
                {
                    displayName: 'Annotation Output Format',
                    name: 'annotationOutputFormat',
                    type: 'options',
                    default: 'json',
                    options: [
                        { name: 'JSON', value: 'json' },
                        { name: 'Markdown', value: 'markdown' },
                    ],
                    displayOptions: {
                        show: {
                            enableDocumentAnnotation: [true],
                        },
                    },
                },
                {
                    displayName: 'Annotation Prompt',
                    name: 'annotationPrompt',
                    type: 'string',
                    typeOptions: { rows: 4 },
                    default: '',
                    displayOptions: {
                        show: {
                            enableDocumentAnnotation: [true],
                        },
                    },
                },
                {
                    displayName: 'Annotation Schema (JSON)',
                    name: 'annotationSchema',
                    type: 'json',
                    default: '',
                    displayOptions: {
                        show: {
                            enableDocumentAnnotation: [true],
                            annotationOutputFormat: ['json'],
                        },
                    },
                },
                {
                    displayName: 'Additional Options',
                    name: 'additionalOptions',
                    type: 'collection',
                    default: {},
                    placeholder: 'Add Option',
                    options: [
                        {
                            displayName: 'Return Raw Response',
                            name: 'returnRawResponse',
                            type: 'boolean',
                            default: false,
                        },
                        {
                            displayName: 'Normalize Output',
                            name: 'normalizeOutput',
                            type: 'boolean',
                            default: true,
                        },
                    ],
                },
            ],
        };
    }
    async execute() {
        var _a, _b, _c, _d, _e, _f, _g, _h;
        const items = this.getInputData();
        const returnData = [];
        for (let itemIndex = 0; itemIndex < items.length; itemIndex++) {
            const binaryPropertyName = this.getNodeParameter('binaryPropertyName', itemIndex, 'data');
            const inputDocumentType = this.getNodeParameter('inputDocumentType', itemIndex, 'auto');
            const modelParam = this.getNodeParameter('model', itemIndex, 'mistral-ocr-latest');
            const useCustomModel = this.getNodeParameter('useCustomModel', itemIndex, false);
            const customModel = useCustomModel
                ? this.getNodeParameter('customModel', itemIndex, '')
                : '';
            const pages = this.getNodeParameter('pages', itemIndex, '').trim();
            const extractTables = this.getNodeParameter('extractTables', itemIndex, 'inline');
            const extractHeader = this.getNodeParameter('extractHeader', itemIndex, false);
            const extractFooter = this.getNodeParameter('extractFooter', itemIndex, false);
            const extractImages = this.getNodeParameter('extractImages', itemIndex, false);
            const imageLimit = extractImages
                ? this.getNodeParameter('imageLimit', itemIndex, 10)
                : 10;
            const minImageSize = extractImages
                ? this.getNodeParameter('minImageSize', itemIndex, 0)
                : 0;
            const extractHyperlinks = this.getNodeParameter('extractHyperlinks', itemIndex, false);
            const enableDocumentAnnotation = this.getNodeParameter('enableDocumentAnnotation', itemIndex, false);
            const perPageAnnotation = this.getNodeParameter('perPageAnnotation', itemIndex, false);
            const annotationOutputFormat = enableDocumentAnnotation
                ? this.getNodeParameter('annotationOutputFormat', itemIndex, 'json')
                : 'json';
            const annotationPrompt = enableDocumentAnnotation
                ? this.getNodeParameter('annotationPrompt', itemIndex, '')
                : '';
            const annotationSchema = enableDocumentAnnotation
                ? this.getNodeParameter('annotationSchema', itemIndex, '')
                : '';
            const additionalOptions = this.getNodeParameter('additionalOptions', itemIndex, {});
            const normalizeOutput = (_a = additionalOptions.normalizeOutput) !== null && _a !== void 0 ? _a : true;
            const returnRawResponse = (_b = additionalOptions.returnRawResponse) !== null && _b !== void 0 ? _b : false;
            const model = useCustomModel ? customModel : modelParam;
            if (!model) {
                throw new n8n_workflow_1.NodeOperationError(this.getNode(), 'Model must be provided', { itemIndex });
            }
            const item = items[itemIndex];
            const binary = (_c = item.binary) === null || _c === void 0 ? void 0 : _c[binaryPropertyName];
            if (!binary) {
                throw new n8n_workflow_1.NodeOperationError(this.getNode(), `Binary data not found at property "${binaryPropertyName}"`, { itemIndex });
            }
            const binaryData = await this.helpers.getBinaryDataBuffer(itemIndex, binaryPropertyName);
            const mimeType = (_d = binary.mimeType) !== null && _d !== void 0 ? _d : inferMimeType(binary.fileName);
            const fileName = (_e = binary.fileName) !== null && _e !== void 0 ? _e : `document-${itemIndex + 1}`;
            const resolvedType = resolveDocumentType(inputDocumentType, mimeType, fileName);
            const basePayload = {
                model,
            };
            if (pages) {
                basePayload.pages = pages;
            }
            if (extractTables !== 'inline') {
                basePayload.table_format = extractTables;
            }
            if (extractHeader) {
                basePayload.extract_header = true;
            }
            if (extractFooter) {
                basePayload.extract_footer = true;
            }
            if (extractImages) {
                basePayload.extract_images = true;
                if (imageLimit > 0)
                    basePayload.image_limit = imageLimit;
                if (minImageSize > 0)
                    basePayload.image_min_size = minImageSize;
            }
            if (extractHyperlinks) {
                basePayload.extract_hyperlinks = true;
            }
            if (enableDocumentAnnotation) {
                if (annotationPrompt.trim()) {
                    basePayload.document_annotation_prompt = annotationPrompt;
                }
                if (annotationOutputFormat === 'json' && annotationSchema && `${annotationSchema}`.trim()) {
                    try {
                        basePayload.document_annotation_format = {
                            type: 'json_schema',
                            json_schema: {
                                name: 'document_annotation',
                                schema: parseJsonSchema(annotationSchema),
                            },
                        };
                    }
                    catch (error) {
                        throw new n8n_workflow_1.NodeOperationError(this.getNode(), error.message, { itemIndex });
                    }
                }
                else if (annotationOutputFormat === 'json') {
                    basePayload.document_annotation_format = { type: 'json_object' };
                }
                else {
                    basePayload.document_annotation_format = { type: 'text' };
                }
            }
            const credentials = await this.getCredentials('mistralCloudApi', itemIndex);
            const apiKey = credentials.apiKey;
            const baseUrl = `${((_f = credentials.baseUrl) !== null && _f !== void 0 ? _f : 'https://api.mistral.ai').replace(/\/$/, '')}`;
            if (!apiKey) {
                throw new n8n_workflow_1.NodeOperationError(this.getNode(), 'Selected Mistral credential is missing an API key', {
                    itemIndex,
                });
            }
            const authHeaders = {
                Authorization: `Bearer ${apiKey}`,
            };
            const ocrEndpoint = `${baseUrl}/v1/ocr`;
            const filesEndpoint = `${baseUrl}/v1/files`;
            let parsedPageRange = null;
            if (pages) {
                try {
                    parsedPageRange = parsePageRange(pages);
                }
                catch (error) {
                    throw new n8n_workflow_1.NodeOperationError(this.getNode(), error.message, { itemIndex });
                }
            }
            const requestOcr = async (payload, pageLabel) => {
                var _a, _b, _c;
                let rawResponse = null;
                let multipartError;
                let jsonOcrError;
                let uploadError;
                try {
                    rawResponse = (await this.helpers.httpRequest.call(this, {
                        method: 'POST',
                        url: ocrEndpoint,
                        json: true,
                        headers: authHeaders,
                        formData: {
                            file: {
                                value: binaryData,
                                options: {
                                    filename: fileName,
                                    contentType: mimeType,
                                },
                            },
                            payload: JSON.stringify(payload),
                        },
                    }));
                }
                catch (error) {
                    multipartError = error;
                    const dataUrl = `data:${mimeType};base64,${binaryData.toString('base64')}`;
                    const documentKey = resolvedType === 'pdf' ? 'document_url' : 'image_url';
                    const documentType = resolvedType === 'pdf' ? 'document_url' : 'image_url';
                    const jsonBody = {
                        ...payload,
                        document: {
                            type: documentType,
                            document_name: fileName,
                            [documentKey]: dataUrl,
                        },
                    };
                    try {
                        rawResponse = (await this.helpers.httpRequest.call(this, {
                            method: 'POST',
                            url: ocrEndpoint,
                            json: true,
                            headers: authHeaders,
                            body: jsonBody,
                        }));
                    }
                    catch (error) {
                        jsonOcrError = error;
                        try {
                            const uploadResponse = (await this.helpers.httpRequest.call(this, {
                                method: 'POST',
                                url: filesEndpoint,
                                json: true,
                                headers: authHeaders,
                                formData: {
                                    purpose: 'ocr',
                                    file: {
                                        value: binaryData,
                                        options: {
                                            filename: fileName,
                                            contentType: mimeType,
                                        },
                                    },
                                },
                            }));
                            const fileId = (_b = (_a = uploadResponse.id) !== null && _a !== void 0 ? _a : uploadResponse.file_id) !== null && _b !== void 0 ? _b : (_c = uploadResponse.data) === null || _c === void 0 ? void 0 : _c.id;
                            if (!fileId) {
                                throw new n8n_workflow_1.NodeOperationError(this.getNode(), 'Mistral file upload did not return a file ID', {
                                    itemIndex,
                                });
                            }
                            const ocrBody = {
                                ...payload,
                                document: {
                                    file_id: fileId,
                                },
                            };
                            rawResponse = (await this.helpers.httpRequest.call(this, {
                                method: 'POST',
                                url: ocrEndpoint,
                                json: true,
                                headers: authHeaders,
                                body: ocrBody,
                            }));
                        }
                        catch (error) {
                            uploadError = error;
                        }
                    }
                }
                if (!rawResponse) {
                    const onPage = pageLabel ? ` for page ${pageLabel}` : '';
                    throw new n8n_workflow_1.NodeOperationError(this.getNode(), [
                        `Mistral OCR failed${onPage} after all request strategies.`,
                        `multipart: ${extractApiErrorMessage(multipartError)}`,
                        `json: ${extractApiErrorMessage(jsonOcrError)}`,
                        `upload: ${extractApiErrorMessage(uploadError)}`,
                    ].join(' '), { itemIndex });
                }
                return rawResponse;
            };
            const explicitPages = parsedPageRange ? toSortedPageArray(parsedPageRange.pages) : [];
            if (perPageAnnotation && explicitPages.length > 1) {
                for (const pageNumber of explicitPages) {
                    const singlePagePayload = {
                        ...basePayload,
                        pages: String(pageNumber),
                    };
                    const pageRawResponse = await requestOcr(singlePagePayload, pageNumber);
                    const singlePageRange = parsePageRange(String(pageNumber));
                    const pageOutput = normalizeOcrResponse(pageRawResponse, {
                        model,
                        mimeType,
                        requestedPages: singlePageRange,
                    });
                    const normalizedPages = (_g = pageOutput.pages) !== null && _g !== void 0 ? _g : [];
                    const page = normalizedPages[0];
                    const perPageItem = {
                        page_index: pageNumber,
                        page,
                        document_annotation: (_h = pageOutput.document_annotation) !== null && _h !== void 0 ? _h : pageRawResponse.document_annotation,
                        meta: {
                            model,
                            requestedPages: parsedPageRange === null || parsedPageRange === void 0 ? void 0 : parsedPageRange.requested,
                            singlePage: pageNumber,
                        },
                    };
                    if (returnRawResponse) {
                        perPageItem.raw = pageRawResponse;
                    }
                    returnData.push({ json: perPageItem });
                }
                continue;
            }
            const rawResponse = await requestOcr(basePayload);
            const outputJson = normalizeOutput
                ? normalizeOcrResponse(rawResponse, {
                    model,
                    mimeType,
                    requestedPages: parsedPageRange,
                })
                : { response: rawResponse };
            if (returnRawResponse) {
                outputJson.raw = rawResponse;
            }
            returnData.push({ json: outputJson });
        }
        return [returnData];
    }
}
exports.MistralDocumentAi = MistralDocumentAi;
function inferMimeType(fileName) {
    if (!fileName)
        return 'application/octet-stream';
    const lower = fileName.toLowerCase();
    if (lower.endsWith('.pdf'))
        return 'application/pdf';
    if (lower.endsWith('.png'))
        return 'image/png';
    if (lower.endsWith('.jpg') || lower.endsWith('.jpeg'))
        return 'image/jpeg';
    if (lower.endsWith('.webp'))
        return 'image/webp';
    if (lower.endsWith('.tif') || lower.endsWith('.tiff'))
        return 'image/tiff';
    return 'application/octet-stream';
}
function resolveDocumentType(inputType, mimeType, fileName) {
    if (inputType !== 'auto') {
        return inputType;
    }
    const lowerMime = mimeType.toLowerCase();
    if (lowerMime.includes('pdf'))
        return 'pdf';
    if (lowerMime.startsWith('image/'))
        return 'image';
    const inferred = inferMimeType(fileName);
    if (inferred.includes('pdf'))
        return 'pdf';
    return 'image';
}
function parsePageRange(value) {
    const pages = new Set();
    const chunks = value.split(',').map((c) => c.trim()).filter(Boolean);
    for (const chunk of chunks) {
        if (chunk.includes('-')) {
            const [startRaw, endRaw] = chunk.split('-').map((x) => x.trim());
            const start = Number(startRaw);
            const end = Number(endRaw);
            if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1 || end < start) {
                throw new Error(`Invalid page range: ${chunk}`);
            }
            for (let p = start; p <= end; p++)
                pages.add(p);
        }
        else {
            const page = Number(chunk);
            if (!Number.isInteger(page) || page < 1) {
                throw new Error(`Invalid page value: ${chunk}`);
            }
            pages.add(page);
        }
    }
    return { requested: value, pages };
}
function toSortedPageArray(pages) {
    return [...pages].sort((a, b) => a - b);
}
function parseJsonSchema(schemaRaw) {
    try {
        const parsed = JSON.parse(schemaRaw);
        if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
            throw new Error('Schema must be a JSON object');
        }
        return parsed;
    }
    catch (error) {
        throw new Error(`Annotation schema must be valid JSON: ${error.message}`);
    }
}
function extractApiErrorMessage(error) {
    var _a, _b, _c;
    if (!error || typeof error !== 'object')
        return 'unknown error';
    const err = error;
    const status = ((_a = err.response) === null || _a === void 0 ? void 0 : _a.status) ? `status ${err.response.status}` : 'no status';
    const data = (_b = err.response) === null || _b === void 0 ? void 0 : _b.data;
    const details = data ? safeStringify(data) : (_c = err.message) !== null && _c !== void 0 ? _c : 'no details';
    return `${status} ${details}`.trim();
}
function safeStringify(value) {
    try {
        if (typeof value === 'string')
            return value;
        return JSON.stringify(value);
    }
    catch {
        return String(value);
    }
}
function normalizeOcrResponse(response, context) {
    var _a, _b;
    const pagesRaw = (_a = response.pages) !== null && _a !== void 0 ? _a : [];
    const pages = pagesRaw
        .map((page, idx) => {
        var _a, _b, _c, _d, _e;
        const candidateIndex = (_b = (_a = (typeof page.index === 'number' && Number.isInteger(page.index) ? page.index : undefined)) !== null && _a !== void 0 ? _a : (typeof page.page_index === 'number' && Number.isInteger(page.page_index) ? page.page_index : undefined)) !== null && _b !== void 0 ? _b : idx + 1;
        const text = (_e = (_d = (_c = page.markdown) !== null && _c !== void 0 ? _c : page.text) !== null && _d !== void 0 ? _d : page.content) !== null && _e !== void 0 ? _e : '';
        return {
            index: candidateIndex,
            markdown: page.markdown,
            text,
            tables: page.tables,
            images: page.images,
            dimensions: page.dimensions,
            header: page.header,
            footer: page.footer,
            hyperlinks: page.hyperlinks,
        };
    })
        .filter((page) => {
        if (!context.requestedPages)
            return true;
        return context.requestedPages.pages.has(page.index);
    });
    return {
        pages,
        document_annotation: response.document_annotation,
        meta: {
            model: context.model,
            inputMimeType: context.mimeType,
            pageCount: pages.length,
            requestedPages: (_b = context.requestedPages) === null || _b === void 0 ? void 0 : _b.requested,
        },
    };
}
//# sourceMappingURL=MistralDocumentAi.node.js.map