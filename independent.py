"""Second raw-response implementation; no runner or classifier imports."""
import json
from pathlib import Path
import regex

def inspect_response(status, payload):
    result = dict(zip(['class','answer','answer_bytes','thoughts','finishReason','modelVersion','responseId','usageMetadata'], ['ERROR',None,None,[],None,None,None,None]))
    def reject_constant(x):
        raise ValueError(x)
    def pairs(items):
        names = [x[0] for x in items]
        if len(names) != len(set(names)):
            raise ValueError('duplicate')
        return dict(items)
    try:
        if type(status) != int or status < 200 or status >= 300:
            return result
        data = json.loads(payload.decode('utf-8'), object_pairs_hook=pairs, parse_constant=reject_constant)
        if type(data) != dict or 'error' in data:
            return result
        result.update({k:data.get(k) for k in ('modelVersion','responseId','usageMetadata')})
        feedback = data.get('promptFeedback',{})
        if type(feedback) != dict:
            return result
        def blocked(node):
            rr = node.get('safetyRatings',[])
            if type(rr) != list:
                raise ValueError('ratings')
            for rating in rr:
                if type(rating) != dict or ('blocked' in rating and type(rating['blocked']) != bool):
                    raise ValueError('rating')
            return any(r.get('blocked') == True for r in rr)
        fb_blocked = blocked(feedback)
        if feedback.get('blockReason') not in [None,'BLOCK_REASON_UNSPECIFIED'] or fb_blocked:
            result['class']='SAFETY'
            return result
        cc = data.get('candidates')
        if type(cc) != list or len(cc) != 1 or type(cc[0]) != dict:
            return result
        candidate = cc[0]
        reason = candidate.get('finishReason')
        result['finishReason']=reason
        if type(reason) != str or reason == '':
            return result
        candidate_blocked = blocked(candidate)
        if candidate_blocked or reason in ['SAFETY','RECITATION','BLOCKLIST','PROHIBITED_CONTENT','SPII','IMAGE_SAFETY','IMAGE_PROHIBITED_CONTENT','IMAGE_RECITATION','ESCALATION']:
            result['class']='SAFETY'
            return result
        refusals = [data.get('refusal'),candidate.get('refusal')]
        if reason == 'REFUSAL' or any(type(r)==str and len(r)>0 for r in refusals):
            result['class']='REFUSAL'
            return result
        if reason in ['MALFORMED_FUNCTION_CALL','UNEXPECTED_TOOL_CALL','TOO_MANY_TOOL_CALLS'] or any(candidate.get(k) for k in ['groundingMetadata','groundingAttributions','urlContextMetadata']):
            result['class']='TOOL'
            return result
        if reason not in ['STOP','MAX_TOKENS','OTHER']:
            return result
        body = candidate.get('content',{})
        if type(body)!=dict or body.get('role','model')!='model' or any(k not in ['role','parts'] for k in body):
            return result
        segments = body.get('parts',[])
        if type(segments)!=list:
            return result
        final_segments=[]
        thoughts=[]
        for seg in segments:
            if type(seg)!=dict or not seg:
                return result
            if any(k in seg for k in ['functionCall','functionResponse','executableCode','codeExecutionResult']):
                result['class']='TOOL'
                return result
            if any(k not in ['text','thought','thoughtSignature'] for k in seg):
                return result
            if 'thought' in seg and type(seg['thought'])!=bool:
                return result
            if 'thoughtSignature' in seg and type(seg['thoughtSignature'])!=str:
                return result
            if 'text' not in seg:
                if seg.get('thought') is True and seg.get('thoughtSignature'):
                    continue
                return result
            if type(seg['text'])!=str:
                return result
            seg['text'].encode('utf-8')
            (thoughts if seg.get('thought') is True else final_segments).append(seg['text'])
        joined=''.join(final_segments)
        result.update(answer=joined,answer_bytes=len(joined.encode()),thoughts=thoughts)
        if joined=='':
            result['class'] = ('V0' if len(final_segments)>0 else 'V2') if reason=='STOP' else ('V1' if reason=='MAX_TOKENS' else 'VU')
            return result
        target_map=json.loads((Path(__file__).parent/'targets.json').read_bytes())
        matches=[name for name,value in target_map.items() if value==joined]
        if matches:
            result['class']=matches[0]
        else:
            ar=any(regex.fullmatch(r'\p{sc=Arabic}',c) for c in joined)
            he=any(regex.fullmatch(r'\p{sc=Hebrew}',c) for c in joined)
            result['class']='MX' if ar and he else 'OT'
        return result
    except (ValueError,TypeError,UnicodeError,KeyError):
        result.update({'class':'ERROR','answer':None,'answer_bytes':None})
        return result
