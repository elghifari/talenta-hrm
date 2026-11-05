import { expect, test } from 'vitest';
import { decodeDraft, decodeReceipt, decodeReferences } from './types';

 test('malformed write receipts are uncertain rather than accepted', () => {
    try { decodeDraft({ revision: 1 }, true); throw new Error('accepted'); }
    catch (error) { expect(error).toMatchObject({ writeOutcome: 'uncertain' }); }
    try { decodeReceipt({ id: 'bad' }, true); throw new Error('accepted'); }
    catch (error) { expect(error).toMatchObject({ writeOutcome: 'uncertain' }); }
 });
 test('unconfigured references keep field definitions available', () => {
    expect(decodeReferences({ available: false, version: null, templates: {}, units: [], jobs: [],
      fields: { yayasan: [], guru: [], klinik_umum: [] } }).available).toBe(false);
 });
