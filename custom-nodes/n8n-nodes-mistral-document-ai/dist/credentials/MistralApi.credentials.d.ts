import type { ICredentialType, INodeProperties } from 'n8n-workflow';
export declare class MistralApi implements ICredentialType {
    name: string;
    displayName: string;
    documentationUrl: string;
    properties: INodeProperties[];
    authenticate: ICredentialType['authenticate'];
}
