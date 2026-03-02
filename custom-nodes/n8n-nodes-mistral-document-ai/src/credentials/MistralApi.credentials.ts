import type { ICredentialType, INodeProperties } from 'n8n-workflow';

export class MistralApi implements ICredentialType {
  name = 'mistralApi';

  displayName = 'Mistral API';

  documentationUrl = 'https://docs.mistral.ai/capabilities/document_ai/basic_ocr/';

  properties: INodeProperties[] = [
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

  authenticate: ICredentialType['authenticate'] = {
    type: 'generic',
    properties: {
      headers: {
        Authorization: '=Bearer {{$credentials.apiKey}}',
      },
    },
  };
}
