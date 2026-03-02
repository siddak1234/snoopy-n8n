"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MistralApi = void 0;
class MistralApi {
    constructor() {
        this.name = 'mistralApi';
        this.displayName = 'Mistral API';
        this.documentationUrl = 'https://docs.mistral.ai/capabilities/document_ai/basic_ocr/';
        this.properties = [
            {
                displayName: 'API Key',
                name: 'apiKey',
                type: 'string',
                typeOptions: {
                    password: true,
                },
                default: '',
                required: true,
            },
            {
                displayName: 'Base URL',
                name: 'baseUrl',
                type: 'string',
                default: 'https://api.mistral.ai',
                required: true,
            },
        ];
        this.authenticate = {
            type: 'generic',
            properties: {
                headers: {
                    Authorization: '=Bearer {{$credentials.apiKey}}',
                },
            },
        };
    }
}
exports.MistralApi = MistralApi;
//# sourceMappingURL=MistralApi.credentials.js.map