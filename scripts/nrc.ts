export const NRC_BASE='https://www.nrc.gov/sites/default/files/doc_library/cdn/data/performance-indicators';
export const NRC_PAGE='https://www.nrc.gov/reactors/operating/oversight/docket-pim?docket=pali';
export type RecordLink={number:string;accession:string;url:string};
export type LiveFinding={id:string;title:string;category:string;rating:string;type:string;by:string;date:string;summary:string;reports:RecordLink[]};
export type Feed={fetchedAt:string;sourceUpdatedAt:string;quarter:string;sourceUrl:string;findings:LiveFinding[];reports:RecordLink[];securityDetailsAvailable:boolean;retrieval?:string};
function plain(v:unknown){if(typeof v!=='string')return '';const entities:Record<string,string>={nbsp:' ',amp:'&',lt:'<',gt:'>',quot:'"',apos:"'",ldquo:'“',rdquo:'”',lsquo:'‘',rsquo:'’',ndash:'–',mdash:'—'};return v.replace(/<[^>]*>/g,' ').replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi,(_,e:string)=>{if(e[0]==='#'){const n=e[1].toLowerCase()==='x'?parseInt(e.slice(2),16):Number(e.slice(1));return n>0&&n<=0x10ffff?String.fromCodePoint(n):''}return entities[e]||' ';}).replace(/\s+/g,' ').trim()}
function link(v:any):RecordLink {const url=new URL(v.ReportUrl,'https://www.nrc.gov');if(url.origin!=='https://www.nrc.gov')throw Error('Unexpected NRC report URL');return {number:String(v.ReportNumber),accession:String(v.AccessionNumber),url:url.href};}
export function normalizeNrc(data:any,sourceUrl:string,fetchedAt:string):Feed{
 if(data?.DocketNum!=='05000255'||typeof data.UpdatedDate!=='string'||typeof data.Quarter!=='string')throw Error('The NRC response format has changed.');
 const keys=['IeFindings','MsFindings','BiFindings','EpFindings','OrsFindings','PrsFindings','SecFindings','MiscFindings'];
 const findings:LiveFinding[]=[];
 for(const key of keys){if(data[key]===null&&key==='SecFindings')continue;if(!Array.isArray(data[key]))throw Error('The NRC findings list is incomplete.');for(const f of data[key]){
 if(typeof f.Title!=='string'||!Array.isArray(f.Reports))throw Error('The NRC finding format has changed.');const reports=f.Reports.map(link);
 findings.push({id:[key,f.Title,f.EventDate,...reports.map((r:RecordLink)=>r.number)].join('|'),title:plain(f.Title),category:plain(f.CornerstoneDesc),rating:plain(f.SignificanceDesc)||'Not specified',type:plain(f.EnforcementActionTypeDesc)||'Not specified',by:plain(f.IdentifiedByDesc)||'Not specified',date:plain(f.EventDate),summary:plain(f.Description),reports});}}
 findings.sort((a,b)=>Date.parse(b.date)-Date.parse(a.date));
 const unique=[...new Map(findings.map(f=>[f.id,f])).values()];const reports=[...new Map(unique.flatMap(f=>f.reports).map(r=>[r.accession,r])).values()];
 return {fetchedAt,sourceUpdatedAt:data.UpdatedDate,quarter:data.Quarter,sourceUrl,findings:unique,reports,securityDetailsAvailable:data.SecFindings!==null};
}
