import {
	NodeOperationError,
	type IDataObject,
	type IExecuteFunctions,
	type IHttpRequestOptions,
	type INodeExecutionData,
	type INodeType,
	type INodeTypeDescription,
} from 'n8n-workflow';

type ExtractTablesMode = 'inline' | 'markdown' | 'html';
type InputDocType = 'auto' | 'pdf' | 'image';

type ParsedPageRange = {
	requested: string;
	pages: Set<number>;
};

export class MistralDocumentAi implements INodeType {
	description: INodeTypeDescription = {
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

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];

		for (let itemIndex = 0; itemIndex < items.length; itemIndex++) {
			const binaryPropertyName = this.getNodeParameter('binaryPropertyName', itemIndex) as string;
			const inputDocumentType = this.getNodeParameter('inputDocumentType', itemIndex) as InputDocType;
			const modelParam = this.getNodeParameter('model', itemIndex) as string;
			const useCustomModel = this.getNodeParameter('useCustomModel', itemIndex) as boolean;
			const customModel = this.getNodeParameter('customModel', itemIndex) as string;
			const pages = (this.getNodeParameter('pages', itemIndex) as string).trim();
			const extractTables = this.getNodeParameter('extractTables', itemIndex) as ExtractTablesMode;
			const extractHeader = this.getNodeParameter('extractHeader', itemIndex) as boolean;
			const extractFooter = this.getNodeParameter('extractFooter', itemIndex) as boolean;
			const extractImages = this.getNodeParameter('extractImages', itemIndex) as boolean;
			const imageLimit = this.getNodeParameter('imageLimit', itemIndex) as number;
			const minImageSize = this.getNodeParameter('minImageSize', itemIndex) as number;
			const extractHyperlinks = this.getNodeParameter('extractHyperlinks', itemIndex) as boolean;
			const enableDocumentAnnotation = this.getNodeParameter('enableDocumentAnnotation', itemIndex) as boolean;
			const annotationOutputFormat = this.getNodeParameter('annotationOutputFormat', itemIndex) as 'json' | 'markdown';
			const annotationPrompt = this.getNodeParameter('annotationPrompt', itemIndex) as string;
			const annotationSchema = this.getNodeParameter('annotationSchema', itemIndex) as string;
			const additionalOptions = this.getNodeParameter('additionalOptions', itemIndex) as IDataObject;

			const normalizeOutput = (additionalOptions.normalizeOutput as boolean | undefined) ?? true;
			const returnRawResponse = (additionalOptions.returnRawResponse as boolean | undefined) ?? false;
			const model = useCustomModel ? customModel : modelParam;

			if (!model) {
				throw new NodeOperationError(this.getNode(), 'Model must be provided', { itemIndex });
			}

			const item = items[itemIndex];
			const binary = item.binary?.[binaryPropertyName];
			if (!binary) {
				throw new NodeOperationError(
					this.getNode(),
					`Binary data not found at property "${binaryPropertyName}"`,
					{ itemIndex },
				);
			}

			const binaryData = await this.helpers.getBinaryDataBuffer(itemIndex, binaryPropertyName);
			const mimeType = binary.mimeType ?? inferMimeType(binary.fileName);
			const fileName = binary.fileName ?? `document-${itemIndex + 1}`;
			const resolvedType = resolveDocumentType(inputDocumentType, mimeType, fileName);

			const basePayload: IDataObject = {
				model,
				document_type: resolvedType,
				table_format: extractTables === 'inline' ? null : extractTables,
				extract_header: extractHeader,
				extract_footer: extractFooter,
			};

			if (pages) {
				basePayload.pages = pages;
			}
			if (extractImages) {
				basePayload.extract_images = true;
				if (imageLimit > 0) basePayload.image_limit = imageLimit;
				if (minImageSize > 0) basePayload.min_image_size = minImageSize;
			}
			if (extractHyperlinks) {
				basePayload.extract_hyperlinks = true;
			}
			if (enableDocumentAnnotation) {
				const annotation: IDataObject = {
					format: annotationOutputFormat,
				};
				if (annotationPrompt.trim()) {
					annotation.prompt = annotationPrompt;
				}
				if (annotationOutputFormat === 'json' && annotationSchema && `${annotationSchema}`.trim()) {
					try {
						annotation.schema = parseJsonSchema(annotationSchema);
					} catch (error) {
						throw new NodeOperationError(this.getNode(), (error as Error).message, { itemIndex });
					}
				}
				basePayload.document_annotation = annotation;
			}

			const credentials = await this.getCredentials('mistralCloudApi', itemIndex);
			const apiKey = credentials.apiKey as string | undefined;
			const baseUrl = `${((credentials.baseUrl as string | undefined) ?? 'https://api.mistral.ai').replace(/\/$/, '')}`;
			if (!apiKey) {
				throw new NodeOperationError(this.getNode(), 'Selected Mistral credential is missing an API key', {
					itemIndex,
				});
			}
			const authHeaders = {
				Authorization: `Bearer ${apiKey}`,
			};
			const ocrEndpoint = `${baseUrl}/v1/ocr`;
			const filesEndpoint = `${baseUrl}/v1/files`;

			let rawResponse: IDataObject;

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
						payload: JSON.stringify(basePayload),
					},
				} as IHttpRequestOptions)) as IDataObject;
			} catch {
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
				} as IHttpRequestOptions)) as IDataObject;

				const fileId =
					(uploadResponse.id as string | undefined) ??
					(uploadResponse.file_id as string | undefined) ??
					(uploadResponse.data as IDataObject | undefined)?.id;

				if (!fileId) {
					throw new NodeOperationError(this.getNode(), 'Mistral file upload did not return a file ID', {
						itemIndex,
					});
				}

				const ocrBody: IDataObject = {
					...basePayload,
					document: {
						type: 'file_id',
						file_id: fileId,
					},
				};

				rawResponse = (await this.helpers.httpRequest.call(this, {
					method: 'POST',
					url: ocrEndpoint,
					json: true,
					headers: authHeaders,
					body: ocrBody,
				} as IHttpRequestOptions)) as IDataObject;
			}

			let parsedPageRange: ParsedPageRange | null = null;
			if (pages) {
				try {
					parsedPageRange = parsePageRange(pages);
				} catch (error) {
					throw new NodeOperationError(this.getNode(), (error as Error).message, { itemIndex });
				}
			}
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

function inferMimeType(fileName?: string): string {
	if (!fileName) return 'application/octet-stream';
	const lower = fileName.toLowerCase();
	if (lower.endsWith('.pdf')) return 'application/pdf';
	if (lower.endsWith('.png')) return 'image/png';
	if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return 'image/jpeg';
	if (lower.endsWith('.webp')) return 'image/webp';
	if (lower.endsWith('.tif') || lower.endsWith('.tiff')) return 'image/tiff';
	return 'application/octet-stream';
}

function resolveDocumentType(inputType: InputDocType, mimeType: string, fileName?: string): 'pdf' | 'image' {
	if (inputType !== 'auto') {
		return inputType;
	}

	const lowerMime = mimeType.toLowerCase();
	if (lowerMime.includes('pdf')) return 'pdf';
	if (lowerMime.startsWith('image/')) return 'image';

	const inferred = inferMimeType(fileName);
	if (inferred.includes('pdf')) return 'pdf';
	return 'image';
}

function parsePageRange(value: string): ParsedPageRange {
	const pages = new Set<number>();
	const chunks = value.split(',').map((c) => c.trim()).filter(Boolean);
	for (const chunk of chunks) {
		if (chunk.includes('-')) {
			const [startRaw, endRaw] = chunk.split('-').map((x) => x.trim());
			const start = Number(startRaw);
			const end = Number(endRaw);
			if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1 || end < start) {
				throw new Error(`Invalid page range: ${chunk}`);
			}
			for (let p = start; p <= end; p++) pages.add(p);
		} else {
			const page = Number(chunk);
			if (!Number.isInteger(page) || page < 1) {
				throw new Error(`Invalid page value: ${chunk}`);
			}
			pages.add(page);
		}
	}
	return { requested: value, pages };
}

function parseJsonSchema(schemaRaw: string): IDataObject {
	try {
		const parsed = JSON.parse(schemaRaw);
		if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
			throw new Error('Schema must be a JSON object');
		}
		return parsed as IDataObject;
	} catch (error) {
		throw new Error(`Annotation schema must be valid JSON: ${(error as Error).message}`);
	}
}

function normalizeOcrResponse(
	response: IDataObject,
	context: {
		model: string;
		mimeType: string;
		requestedPages: ParsedPageRange | null;
	},
): IDataObject {
	const pagesRaw = (response.pages as IDataObject[] | undefined) ?? [];
	const pages = pagesRaw
		.map((page, idx) => {
			const candidateIndex =
				(typeof page.index === 'number' && Number.isInteger(page.index) ? (page.index as number) : undefined) ??
				(typeof page.page_index === 'number' && Number.isInteger(page.page_index) ? (page.page_index as number) : undefined) ??
				idx + 1;
			const text =
				(page.markdown as string | undefined) ??
				(page.text as string | undefined) ??
				(page.content as string | undefined) ??
				'';

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
			if (!context.requestedPages) return true;
			return context.requestedPages.pages.has(page.index);
		});

	return {
		pages,
		document_annotation: response.document_annotation,
		meta: {
			model: context.model,
			inputMimeType: context.mimeType,
			pageCount: pages.length,
			requestedPages: context.requestedPages?.requested,
		},
	};
}
