"""Gemini-native, byte-exact classification. Never imports a network client."""
import json
import regex
from common import ROOT, read

CLASSES = ('T1','T0','GEMINI_ORIGINAL','HE','SHART','SHAMS','MX','OT','V0','V2','V1','VU','SAFETY','REFUSAL','TOOL','ERROR')
BLOCKS = {'SAFETY','RECITATION','BLOCKLIST','PROHIBITED_CONTENT','SPII','IMAGE_SAFETY','IMAGE_PROHIBITED_CONTENT','IMAGE_RECITATION','ESCALATION'}
TOOLS = {'MALFORMED_FUNCTION_CALL','UNEXPECTED_TOOL_CALL','TOO_MANY_TOOL_CALLS'}

def classify(status, raw):
    out = {'class':'ERROR','answer':None,'answer_bytes':None,'thoughts':[], 'finishReason':None, 'modelVersion':None, 'responseId':None, 'usageMetadata':None}
    try:
        if type(status) is not int or not 200 <= status < 300:
            return out
        def unique(pairs):
            d = {}
            for k,v in pairs:
                if k in d:
                    raise ValueError('duplicate JSON key')
                d[k] = v
            return d
        obj = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        if not isinstance(obj,dict) or 'error' in obj:
            return out
        for k in ['modelVersion','responseId','usageMetadata']:
            out[k] = obj.get(k)
        feedback = obj.get('promptFeedback',{})
        if not isinstance(feedback,dict):
            return out
        ratings = feedback.get('safetyRatings',[])
        if not isinstance(ratings,list) or any(not isinstance(r,dict) or ('blocked' in r and type(r['blocked']) is not bool) for r in ratings):
            return out
        if feedback.get('blockReason') not in (None,'BLOCK_REASON_UNSPECIFIED') or any(r.get('blocked') is True for r in ratings):
            out['class'] = 'SAFETY'
            return out
        candidates = obj.get('candidates')
        if not isinstance(candidates,list) or len(candidates) != 1 or not isinstance(candidates[0],dict):
            return out
        c = candidates[0]
        finish = c.get('finishReason')
        out['finishReason'] = finish
        if not isinstance(finish,str) or not finish:
            return out
        ratings = c.get('safetyRatings',[])
        if not isinstance(ratings,list) or any(not isinstance(r,dict) or ('blocked' in r and type(r['blocked']) is not bool) for r in ratings):
            return out
        if finish in BLOCKS or any(r.get('blocked') is True for r in ratings):
            out['class'] = 'SAFETY'
            return out
        # No documented Gemini refusal field currently. Preserve an explicit
        # nonempty string extension conservatively; never infer it from prose.
        if any(isinstance(v,str) and bool(v) for v in (obj.get('refusal'),c.get('refusal'))) or finish == 'REFUSAL':
            out['class'] = 'REFUSAL'
            return out
        if finish in TOOLS or any(c.get(k) for k in ('groundingMetadata','groundingAttributions','urlContextMetadata')):
            out['class'] = 'TOOL'
            return out
        if finish not in {'STOP','MAX_TOKENS','OTHER'}:
            return out
        content = c.get('content',{})
        if not isinstance(content,dict) or content.get('role','model') != 'model' or set(content)-{'role','parts'}:
            return out
        parts = content.get('parts',[])
        if not isinstance(parts,list):
            return out
        answer, thoughts, present = [], [], False
        for part in parts:
            if not isinstance(part,dict) or not part:
                return out
            if any(k in part for k in ('functionCall','functionResponse','executableCode','codeExecutionResult')):
                out['class'] = 'TOOL'
                return out
            if set(part)-{'text','thought','thoughtSignature'} or ('thought' in part and type(part['thought']) is not bool):
                return out
            if 'thoughtSignature' in part and not isinstance(part['thoughtSignature'],str):
                return out
            if 'text' not in part:
                if part.get('thought') is True and part.get('thoughtSignature'):
                    continue
                return out
            if not isinstance(part['text'],str):
                return out
            part['text'].encode('utf-8')
            if part.get('thought') is True:
                thoughts.append(part['text'])
            else:
                present = True
                answer.append(part['text'])
        text = ''.join(answer)
        out.update(answer=text, answer_bytes=len(text.encode('utf-8')), thoughts=thoughts)
        if text:
            targets = read(ROOT/'targets.json')
            exact = next((k for k,v in targets.items() if v == text),None)
            out['class'] = exact or ('MX' if regex.search(r'\p{Script=Arabic}',text) and regex.search(r'\p{Script=Hebrew}',text) else 'OT')
        elif finish == 'STOP':
            out['class'] = 'V0' if present else 'V2'
        elif finish == 'MAX_TOKENS':
            out['class'] = 'V1'
        else:
            out['class'] = 'VU'
        return out
    except (ValueError,TypeError,UnicodeError,KeyError):
        out.update({'class':'ERROR','answer':None,'answer_bytes':None})
        return out
