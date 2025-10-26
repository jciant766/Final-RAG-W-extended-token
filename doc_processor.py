import re
import tiktoken
import json
from typing import List, Dict, Any
from debug_logger import DebugLogger

class DocumentProcessor:
    def __init__(self):
        self.debug = DebugLogger("doc_processor")
        self.encoding = tiktoken.get_encoding("cl100k_base")
        # Increased to allow near-whole-article chunks and reduce splitting
        self.max_tokens = 3000
        # Maximum overlap for legal precision - ensures absolutely no context loss
        self.overlap_tokens = 1000  # 33% overlap - maximum for legal documents
        # Document-aware fields (set per processed file - will be updated per document)
        self.citation_prefix = "Commercial Code (Cap. 13)"
        self.citation_label = "Art."
        self.id_label = "article"
        self.doc_code = "code_13"
        self.source_file = None
        
        # Comprehensive document overviews for AI context enrichment
        self.doc_overviews = {
            "cap_12": "Code of Organization and Civil Procedure (Cap. 12): Governs court organization, civil litigation procedures, jurisdiction, evidence, appeals, enforcement of judgments, and civil procedural law in Malta.",
            "cap_123": "Income Tax Act (Cap. 123): Comprehensive income tax legislation covering taxation of individuals and companies, tax rates, deductions, exemptions, capital allowances, tax credits, double taxation relief, and tax administration.",
            "cap_16": "Civil Code (Cap. 16): Comprehensive civil law governing persons, family law, succession, property rights, ownership, servitudes, usufruct, contracts, obligations, torts, prescription, and general civil legal relationships in Malta.",
            "cap_246": "AIP Act (Cap. 246): Acquist Impost Proprium (Property Tax) legislation governing property tax assessment, valuation, rates, exemptions, collection, appeals, and local council funding.",
            "cap_296": "Land Registration Act (Cap. 296): Governs land registration system, public registry, property title registration, encumbrances, mortgages, easements, searches, and property transaction documentation.",
            "cap_364": "Duty on Documents and Transfers Act (Cap. 364): Regulates stamp duty on documents, property transfers, share transfers, mortgages, leases, rates, exemptions, collection procedures, and duty assessment.",
            "cap_372": "Income Tax Management Act (Cap. 372): Governs income tax administration, assessment procedures, appeals, collection, enforcement, penalties, interest, tax returns, and Commissioner for Revenue powers.",
            "cap_373": "Prevention of Money Laundering Act (Cap. 373): Anti-money laundering and terrorist financing legislation covering customer due diligence, reporting obligations, compliance, Financial Intelligence Analysis Unit (FIAU), penalties, and preventive measures.",
            "cap_398": "Condominium Act (Cap. 398): Regulates condominium property, common parts, individual units, administrator duties, general meetings, decision-making, maintenance, insurance, and condominium governance.",
            "cap_540": "Gender Identity, Gender Expression and Sex Characteristics Act (Cap. 540): Protects rights related to gender identity, gender expression, sex characteristics, legal recognition, medical interventions, and anti-discrimination provisions.",
            "cap_55": "Notarial Profession and Notarial Archives Act (Cap. 55): Regulates notarial profession, admission requirements, notarial duties, ethics, public deeds, notarial archives, Notarial Council, disciplinary procedures, and professional standards.",
            "cap_56": "Public Registry Act (Cap. 56): Governs public registry operations, registration of public deeds, property transactions, mortgages, privileges, searches, registry procedures, and Registrar duties.",
            "cap_604": "Private Residential Leases Act (Cap. 604): Governs residential lease agreements, rent regulation, tenant and landlord rights, lease termination, eviction procedures, rent increases, and dispute resolution.",
            "cap_614": "Cohabitation Act (Cap. 614): Regulates cohabitation relationships, registration, rights and obligations of cohabitants, property rights, succession rights, termination, and legal protection.",
            "cap_615": "Real Estate Agents, Property Brokers and Property Consultants Act (Cap. 615): Regulates real estate profession, licensing, professional conduct, duties to clients, advertising, commissions, complaints, and disciplinary measures.",
            "cap_79": "Commissioners for Oaths Ordinance (Cap. 79): Governs appointment and duties of commissioners for oaths, administration of oaths, affidavits, declarations, and authentication of documents.",
            "code_13": "Malta's primary commercial law governing traders, acts of trade, bills of exchange, promissory notes, maritime insurance, bottomry, salvage, general average, commercial transactions, bankruptcy, commercial disputes, and merchant regulations.",
            "eu_succession_regulation_650": "EU Succession Regulation - 650.2012: European Union Regulation on jurisdiction, applicable law, recognition and enforcement of decisions, and cooperation in matters of succession, applicable in Malta.",
            "sl_123_198": "Assignments of Rights Acquired under a Promise of Sale Agreement (S.L. 123.198): Regulates assignment of property sale rights, tax treatment, documentation, and procedural requirements.",
            "sl_123_203": "UCA & Vacant Property (S.L. 123.203): Urban Conservation Area and vacant property tax provisions, rates, exemptions, and penalties under Income Tax Act.",
            "sl_123_27": "Capital Gains Rules (S.L. 123.27): Subsidiary legislation under Income Tax Act governing capital gains taxation, exemptions, rates, calculation methods, and reporting requirements.",
            "sl_123_92": "Tax on Property Transfers Rules (S.L. 123.92): Rules governing tax on property transfers, rates, calculation, exemptions, payment procedures, and compliance requirements.",
            "sl_16_14": "Termination of Mandates (S.L. 16.14): Regulations governing termination of mandates, agency relationships, and power of attorney under Civil Code.",
            "sl_246_04": "AIP Values (S.L. 246.04): Property valuation methodology and rates for Acquist Impost Proprium (property tax) assessment.",
            "sl_296_01": "Land Registration Rules (S.L. 296.01): Detailed procedures for land registration, forms, fees, timelines, and registry operations.",
            "sl_296_08": "Submission of Plans Rules (S.L. 296.08): Requirements for submitting architectural plans, surveys, and property documentation to land registry.",
            "sl_364_01": "Old Duty Exemptions (S.L. 364.01): Historical duty exemptions under Duty on Documents and Transfers Act.",
            "sl_364_06": "Duty on Documents and Transfers Rules (S.L. 364.06): Detailed rules for stamp duty calculation, payment procedures, exemptions, and administrative processes.",
            "sl_364_12": "First Time Buyers & Gozo Exemptions (S.L. 364.12): Stamp duty exemptions for first-time property buyers and properties in Gozo, eligibility criteria, and application procedures.",
            "sl_364_15": "Donation of Shares (S.L. 364.15): Duty regulations for share donations, rates, exemptions, and procedural requirements.",
            "sl_364_17": "Second Time Buyers (S.L. 364.17): Stamp duty provisions for second-time property buyers, rates, and eligibility conditions.",
            "sl_364_18": "New Causa Mortis Interest Rate (S.L. 364.18): Interest rates for inheritance and succession duty calculations.",
            "sl_364_19": "UCA & Vacant Property (S.L. 364.19): Urban Conservation Area and vacant property duty provisions under stamp duty legislation.",
            "sl_373_01": "Prevention of Money Laundering Regulations (S.L. 373.01): Detailed AML/CFT regulations including customer due diligence, record keeping, reporting, compliance programs, and supervisory requirements.",
            "sl_373_04": "Use of Cash (Restriction) Regulations (S.L. 373.04): Restrictions on cash transactions, limits, exemptions, reporting, and penalties for money laundering prevention.",
            "sl_398_01": "Condominium Regulations (S.L. 398.01): Detailed regulations for condominium administration, meetings, voting, maintenance, insurance, and dispute resolution.",
            "sl_55_01": "Functions & Duties of the Notarial College and Notarial Council (S.L. 55.01): Governance structure, responsibilities, and procedures of notarial professional bodies.",
            "sl_55_05": "Acts of Deceased Notaries Regulations (S.L. 55.05): Procedures for managing notarial acts and archives of deceased notaries, custody, and access.",
            "sl_55_06": "Examination of Title Regulations (S.L. 55.06): Notarial duties and procedures for examining property titles, due diligence requirements, and liability standards.",
            "sl_55_07": "Notaries (Compulsory Insurance) Regulations (S.L. 55.07): Professional indemnity insurance requirements for notaries, coverage amounts, and compliance obligations.",
            "sl_55_09": "Code of Ethics (S.L. 55.09): Professional ethics code for notaries covering conduct standards, conflicts of interest, confidentiality, and professional responsibilities.",
            "sl_56_03": "Public Registry (Inspection and Searches) Regulations (S.L. 56.03): Procedures for public registry searches, document inspection, fees, and access rights.",
            "sl_604_02": "Registration of Private Residential Leases Contracts Regulations (S.L. 604.02): Mandatory lease registration procedures, forms, fees, penalties for non-registration, and compliance requirements.",
            "sl_623_01": "EPC Regulations (S.L. 623.01): Energy Performance Certificate requirements for buildings, assessment procedures, validity, penalties, and compliance obligations."
        }
        self.doc_overview = ""
        
    def process_document(self, file_path: str) -> Dict[str, Any]:
        """Process the Malta Commercial Code document"""
        self.debug.log("info", f"Processing document: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Infer document info from file path/name
            self._infer_document_info(file_path)
            
            # Pre-clean OCR artifacts before article extraction
            content = self._preclean_document_text(content)
            
            # Clean and extract articles
            articles = self._extract_articles(content)
            self.debug.log("info", f"Extracted {len(articles)} articles")
            
            # Process each article
            all_chunks = []
            for article in articles:
                chunks = self._create_chunks(article)
                all_chunks.extend(chunks)
            
            # Save processed chunks for indexing
            with open('processed_chunks.json', 'w', encoding='utf-8') as f:
                json.dump(all_chunks, f, ensure_ascii=False)

            # Save processing report
            report = {
                "total_articles": len(articles),
                "total_chunks": len(all_chunks),
                "articles_processed": [a['article'] for a in articles],
                "document": self.citation_prefix
            }
            
            with open('processing_report.json', 'w') as f:
                json.dump(report, f, indent=2)
            
            self.debug.log("info", f"Document processing complete. Created {len(all_chunks)} chunks")
            return report
            
        except Exception as e:
            self.debug.log("error", f"Error processing document: {e}")
            raise
    
    def _preclean_document_text(self, content: str) -> str:
        """Heuristically remove OCR header/footers and stray page numbers.
        Targets patterns observed in Companies Act/Subsidiary Legislation OCR such as:
        - Page headers like "COMPANIES [CAP. 386] 11"
        - Standalone page numbers
        - Markdown heading artifacts (lines starting with '## ')
        - Isolated 'Cap. 386.' lines repeated between blocks
        - Hyphenation across line breaks
        
        IMPORTANT: Preserves page markers like "--- PAGE 1 ---" for proper page attribution.
        """
        text = content
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove markdown heading lines entirely
        text = re.sub(r"(?m)^\s*##\s+.*$", "", text)
        
        # Remove page headers like "COMPANIES [CAP. 386] 11" or similar
        # But be careful not to match our page markers "--- PAGE 1 ---"
        text = re.sub(r"(?m)^\s*[A-Z][A-Z\s\[\]\.\-]*CAP\.?\s*\d+\]?\s*\d+\s*$", "", text)
        
        # Remove isolated Cap. XXX. lines
        text = re.sub(r"(?m)^\s*Cap\.\s*\d+\.?\s*$", "", text)
        
        # Remove pure page number lines, but NOT our page markers
        # Only remove standalone digits, not "--- PAGE N ---" format
        text = re.sub(r"(?m)^\s*\d+\s*$", "", text)
        
        # De-hyphenate line-break splits: "exam-\nple" -> "example"
        # Only match word characters before the hyphen to avoid page markers
        text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
        
        # Collapse multiple blank lines
        text = re.sub(r"\n{2,}", "\n\n", text)
        
        return text

    def _extract_articles(self, content: str) -> List[Dict[str, Any]]:
        """Extract articles using regex over the whole document.
        Matches headings like "547." or "26A." and captures text until next heading or page marker.
        """
        # Precompute page positions from markers to estimate page per article
        page_marker_re = re.compile(r"---\s*PAGE\s*(\d+)\s*---", re.IGNORECASE)
        page_positions: List[Dict[str, int]] = []
        for pm in page_marker_re.finditer(content):
            try:
                page_no = int(pm.group(1))
            except Exception:
                continue
            page_positions.append({"start": pm.start(), "page": page_no})
        page_positions.sort(key=lambda x: x["start"])  # ascending by start index

        # Primary: heading at start of line. Allow dot followed by space OR newline.
        heading_block_re = re.compile(
            r"(?ms)^[\t \u00A0]*([0-9]{1,4}[A-Z]?)\s*\.(?:\s|$)(.*?)(?=^[\t \u00A0]*[0-9]{1,4}[A-Z]?\s*\.(?:\s|$)|^---\s*PAGE\s*\d+\s*---|\Z)"
        )
        # Fallback: anywhere in text, used if primary yields too few articles
        fallback_heading_re = re.compile(r"([0-9]{1,4}[A-Z]?)\s*\.")

        def page_for_index(idx: int) -> int:
            if not page_positions:
                return 1
            # Binary search for last page whose start <= idx
            lo, hi = 0, len(page_positions) - 1
            best = page_positions[0]["page"]
            while lo <= hi:
                mid = (lo + hi) // 2
                if page_positions[mid]["start"] <= idx:
                    best = page_positions[mid]["page"]
                    lo = mid + 1
                else:
                    hi = mid - 1
            return best

        def normalize_article_id(art: str) -> str:
            m = re.match(r"^(0*)(\d+)([A-Z]?)$", art)
            if not m:
                return art
            base = m.group(2)
            suffix = m.group(3)
            return f"{int(base)}{suffix}" if suffix else str(int(base))

        def article_numeric_value(art: str) -> float:
            # Convert like 26A -> 26.1, 26B -> 26.2 etc.
            norm = normalize_article_id(art)
            m = re.match(r"^(\d+)([A-Z]?)$", norm)
            if not m:
                return -1.0
            base = int(m.group(1))
            suffix = m.group(2)
            if not suffix:
                return float(base)
            offset = ord(suffix) - ord('A') + 1
            return float(base) + offset / 10.0

        MAX_ARTICLE = 550
        articles: List[Dict[str, Any]] = []
        prev_val = -1.0
        seen_ids = set()
        for m in heading_block_re.finditer(content):
            art_id = normalize_article_id(m.group(1))
            val = article_numeric_value(art_id)
            if val <= 0 or val > MAX_ARTICLE:
                continue
            if val <= prev_val + 1e-6:
                continue
            raw_text = m.group(2)
            cleaned_content = self._clean_content(raw_text)
            if not cleaned_content:
                continue
            if art_id in seen_ids:
                continue
            seen_ids.add(art_id)
            prev_val = val
            articles.append({
                'article': str(art_id),
                'content': cleaned_content,
                'page': page_for_index(m.start()),
                'position': len(articles) + 1
            })

        # Fallback segmentation if too few articles found
        if len(articles) < 500:
            candidates = list(fallback_heading_re.finditer(content))
            prev_val = prev_val
            for idx, m in enumerate(candidates):
                art_id = normalize_article_id(m.group(1))
                val = article_numeric_value(art_id)
                if val <= 0 or val > MAX_ARTICLE:
                    continue
                if val <= prev_val + 1e-6:
                    continue
                start_idx = m.end()
                # find end index at next valid candidate
                end_idx = len(content)
                for j in range(idx + 1, len(candidates)):
                    next_art = normalize_article_id(candidates[j].group(1))
                    next_val = article_numeric_value(next_art)
                    if next_val > val:
                        end_idx = candidates[j].start()
                        break
                raw_text = content[start_idx:end_idx]
                cleaned_content = self._clean_content(raw_text)
                if not cleaned_content:
                    continue
                if art_id in seen_ids:
                    continue
                seen_ids.add(art_id)
                prev_val = val
                articles.append({
                    'article': str(art_id),
                    'content': cleaned_content,
                    'page': page_for_index(m.start()),
                    'position': len(articles) + 1
                })

            # Sort by numeric article value to stabilize order
            articles.sort(key=lambda a: article_numeric_value(a['article']))

        return articles
    
    def _clean_content(self, content: str) -> str:
        """Clean article content"""
        # Remove page markers if any slipped through
        content = re.sub(r'---\s*PAGE\s*\d+\s*---', ' ', content, flags=re.IGNORECASE)
        # Collapse whitespace
        content = re.sub(r'\s+', ' ', content)
        return content.strip()
    
    def _create_chunks(self, article: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create token-aware chunks from article content"""
        content = article['content']
        tokens = self.encoding.encode(content)
        
        if len(tokens) <= self.max_tokens:
            # Article fits in one chunk
            chunk = self._create_chunk(article, content, 0, 1)
            return [chunk]
        
        # Split into multiple chunks
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(tokens):
            end = min(start + self.max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            
            chunk = self._create_chunk(article, chunk_text, chunk_index, 
                                     (len(tokens) + self.max_tokens - 1) // self.max_tokens)
            chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.overlap_tokens
            chunk_index += 1
            
            # Prevent infinite loop
            if start >= len(tokens) - self.overlap_tokens:
                break
        
        return chunks
    
    def _create_chunk(self, article: Dict[str, Any], content: str, chunk_index: int, total_chunks: int) -> Dict[str, Any]:
        """Create a single chunk with metadata"""
        # Ensure globally unique and document-aware IDs
        chunk_id = (
            f"{self.doc_code}_{self.id_label}_{article['article']}"
            f"_p{article['page']}_pos{article['position']}_chunk_{chunk_index + 1}"
        )
        
        return {
            'id': chunk_id,
            'content': content,
            'metadata': {
                'article': str(article['article']),
                'page': article['page'],
                'position': article['position'],
                'chunk_index': chunk_index,
                'total_chunks': total_chunks,
                'tokens': len(self.encoding.encode(content)),
                'citation': f"{self.citation_prefix} {self.citation_label} {article['article']}",
                'document': self.citation_prefix,
                'id_label': self.id_label,
                'doc_code': self.doc_code,
                'doc_overview': self.doc_overview,
                'source_file': self.source_file or file_path
            }
        }

    def _infer_document_info(self, file_path: str) -> None:
        """Infer document name and metadata from filename.
        Handles patterns like:
        - "16 - Civil Code.txt" → Civil Code (Cap. 16)
        - "123.27 - Capital Gains Rules.txt" → Capital Gains Rules (S.L. 123.27)
        - "malta_commercial_code_text.txt" → Commercial Code (Cap. 13)
        """
        try:
            import os
            import re as _re
            
            base = os.path.basename(file_path)
            stem = os.path.splitext(base)[0]
            
            # Special case: Commercial Code text file
            if "commercial" in stem.lower() and "code" in stem.lower():
                self.citation_prefix = "Commercial Code (Cap. 13)"
                self.citation_label = "Art."
                self.id_label = "article"
                self.doc_code = "code_13"
                self.source_file = base
                self.doc_overview = self.doc_overviews.get(self.doc_code, "")
                return
            
            # Pattern: "123.27 - Capital Gains Rules" (Subsidiary Legislation)
            m = _re.match(r'^(\d+)\.(\d+)\s*-\s*(.+)$', stem)
            if m:
                cap = m.group(1)
                sub = m.group(2)
                name = m.group(3).strip()
                self.citation_prefix = f"{name} (S.L. {cap}.{sub})"
                self.citation_label = "Reg."
                self.id_label = "regulation"
                self.doc_code = f"sl_{cap}_{sub}"
                self.source_file = base
                self.doc_overview = self.doc_overviews.get(self.doc_code, f"{name}: Subsidiary legislation under Chapter {cap}.")
                return
            
            # Pattern: "16 - Civil Code" (Main Acts/Codes)
            m = _re.match(r'^(\d+)\s*-\s*(.+)$', stem)
            if m:
                cap = m.group(1)
                name = m.group(2).strip()
                self.citation_prefix = f"{name} (Cap. {cap})"
                self.citation_label = "Art."
                self.id_label = "article"
                self.doc_code = f"cap_{cap}"
                self.source_file = base
                self.doc_overview = self.doc_overviews.get(self.doc_code, f"{name}: Chapter {cap} of the Laws of Malta.")
                return
            
            # Pattern: "EU Succession Regulation - 650.2012"
            if "EU" in stem.upper() or "REGULATION" in stem.upper():
                self.citation_prefix = stem
                self.citation_label = "Art."
                self.id_label = "article"
                self.doc_code = "eu_" + _re.sub(r'[^\w]+', '_', stem.lower())[:30]
                self.source_file = base
                self.doc_overview = f"{stem}: European Union regulation applicable in Malta."
                return
            
            # Fallback: use filename as-is
            self.citation_prefix = stem
            self.citation_label = "Art."
            self.id_label = "article"
            self.doc_code = _re.sub(r'[^\w]+', '_', stem.lower())[:30]
            self.source_file = base
            self.doc_overview = f"{stem}: Legal document."
            
        except Exception as e:
            self.debug.log("warning", f"Could not infer document info from {file_path}: {e}")
            # Keep existing defaults on failure
            pass