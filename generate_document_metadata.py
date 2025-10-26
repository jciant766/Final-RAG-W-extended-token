#!/usr/bin/env python3
"""
Generate Document Metadata Script
Creates comprehensive overviews for all documents in the vector database
"""

import json
from pathlib import Path

def generate_document_metadata():
    """Generate metadata for all documents"""
    
    # Load processed chunks to see what documents we have
    with open('processed_chunks.json', 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    # Extract unique documents
    documents = {}
    for chunk in chunks:
        md = chunk['metadata']
        doc_name = md.get('document', 'Unknown')
        doc_code = md.get('doc_code', 'unknown')
        source_file = md.get('source_file', '')
        
        if doc_name not in documents:
            documents[doc_name] = {
                'doc_code': doc_code,
                'source_file': source_file,
                'chunk_count': 0
            }
        documents[doc_name]['chunk_count'] += 1
    
    print(f"Found {len(documents)} unique documents")
    print("\n" + "="*80)
    print("DOCUMENT METADATA GENERATION")
    print("="*80 + "\n")
    
    # Comprehensive document metadata
    metadata = {
        # Commercial Code
        "code_13": {
            "name": "Commercial Code (Cap. 13)",
            "overview": "Malta's primary commercial law governing traders, acts of trade, bills of exchange, promissory notes, maritime insurance, bottomry, salvage, general average, commercial transactions, bankruptcy, commercial disputes, and merchant regulations."
        },
        
        # Civil Code
        "cap_16": {
            "name": "Civil Code (Cap. 16)",
            "overview": "Civil Code (Cap. 16): Comprehensive civil law governing persons, family law, succession, property rights, ownership, servitudes, usufruct, contracts, obligations, torts, prescription, and general civil legal relationships in Malta."
        },
        
        # Code of Organization and Civil Procedure
        "cap_12": {
            "name": "Code of Organization and Civil Procedure (Cap. 12)",
            "overview": "Code of Organization and Civil Procedure (Cap. 12): Governs court organization, civil litigation procedures, jurisdiction, evidence, appeals, enforcement of judgments, and civil procedural law in Malta."
        },
        
        # Income Tax Act
        "cap_123": {
            "name": "Income Tax Act (Cap. 123)",
            "overview": "Income Tax Act (Cap. 123): Comprehensive income tax legislation covering taxation of individuals and companies, tax rates, deductions, exemptions, capital allowances, tax credits, double taxation relief, and tax administration."
        },
        
        # Income Tax Management Act
        "cap_372": {
            "name": "Income Tax Management Act (Cap. 372)",
            "overview": "Income Tax Management Act (Cap. 372): Governs income tax administration, assessment procedures, appeals, collection, enforcement, penalties, interest, tax returns, and Commissioner for Revenue powers."
        },
        
        # Duty on Documents and Transfers Act
        "cap_364": {
            "name": "Duty on Documents and Transfers Act (Cap. 364)",
            "overview": "Duty on Documents and Transfers Act (Cap. 364): Regulates stamp duty on documents, property transfers, share transfers, mortgages, leases, rates, exemptions, collection procedures, and duty assessment."
        },
        
        # Land Registration Act
        "cap_296": {
            "name": "Land Registration Act (Cap. 296)",
            "overview": "Land Registration Act (Cap. 296): Governs land registration system, public registry, property title registration, encumbrances, mortgages, easements, searches, and property transaction documentation."
        },
        
        # Prevention of Money Laundering Act
        "cap_373": {
            "name": "Prevention of Money Laundering Act (Cap. 373)",
            "overview": "Prevention of Money Laundering Act (Cap. 373): Anti-money laundering and terrorist financing legislation covering customer due diligence, reporting obligations, compliance, Financial Intelligence Analysis Unit (FIAU), penalties, and preventive measures."
        },
        
        # Notarial Profession and Notarial Archives Act
        "cap_55": {
            "name": "Notarial Profession and Notarial Archives Act (Cap. 55)",
            "overview": "Notarial Profession and Notarial Archives Act (Cap. 55): Regulates notarial profession, admission requirements, notarial duties, ethics, public deeds, notarial archives, Notarial Council, disciplinary procedures, and professional standards."
        },
        
        # Public Registry Act
        "cap_56": {
            "name": "Public Registry Act (Cap. 56)",
            "overview": "Public Registry Act (Cap. 56): Governs public registry operations, registration of public deeds, property transactions, mortgages, privileges, searches, registry procedures, and Registrar duties."
        },
        
        # Condominium Act
        "cap_398": {
            "name": "Condominium Act (Cap. 398)",
            "overview": "Condominium Act (Cap. 398): Regulates condominium property, common parts, individual units, administrator duties, general meetings, decision-making, maintenance, insurance, and condominium governance."
        },
        
        # Private Residential Leases Act
        "cap_604": {
            "name": "Private Residential Leases Act (Cap. 604)",
            "overview": "Private Residential Leases Act (Cap. 604): Governs residential lease agreements, rent regulation, tenant and landlord rights, lease termination, eviction procedures, rent increases, and dispute resolution."
        },
        
        # Cohabitation Act
        "cap_614": {
            "name": "Cohabitation Act (Cap. 614)",
            "overview": "Cohabitation Act (Cap. 614): Regulates cohabitation relationships, registration, rights and obligations of cohabitants, property rights, succession rights, termination, and legal protection."
        },
        
        # Real Estate Agents Act
        "cap_615": {
            "name": "Real Estate Agents, Property Brokers and Property Consultants Act (Cap. 615)",
            "overview": "Real Estate Agents, Property Brokers and Property Consultants Act (Cap. 615): Regulates real estate profession, licensing, professional conduct, duties to clients, advertising, commissions, complaints, and disciplinary measures."
        },
        
        # AIP Act
        "cap_246": {
            "name": "AIP Act (Cap. 246)",
            "overview": "AIP Act (Cap. 246): Acquist Impost Proprium (Property Tax) legislation governing property tax assessment, valuation, rates, exemptions, collection, appeals, and local council funding."
        },
        
        # Gender Identity Act
        "cap_540": {
            "name": "Gender Identity, Gender Expression and Sex Characteristics Act (Cap. 540)",
            "overview": "Gender Identity, Gender Expression and Sex Characteristics Act (Cap. 540): Protects rights related to gender identity, gender expression, sex characteristics, legal recognition, medical interventions, and anti-discrimination provisions."
        },
        
        # Commissioners for Oaths
        "cap_79": {
            "name": "Commissioners for Oaths Ordinance (Cap. 79)",
            "overview": "Commissioners for Oaths Ordinance (Cap. 79): Governs appointment and duties of commissioners for oaths, administration of oaths, affidavits, declarations, and authentication of documents."
        },
        
        # Subsidiary Legislation - Tax
        "sl_123_27": {
            "name": "Capital Gains Rules (S.L. 123.27)",
            "overview": "Capital Gains Rules (S.L. 123.27): Subsidiary legislation under Income Tax Act governing capital gains taxation, exemptions, rates, calculation methods, and reporting requirements."
        },
        
        "sl_123_92": {
            "name": "Tax on Property Transfers Rules (S.L. 123.92)",
            "overview": "Tax on Property Transfers Rules (S.L. 123.92): Rules governing tax on property transfers, rates, calculation, exemptions, payment procedures, and compliance requirements."
        },
        
        "sl_123_198": {
            "name": "Assignments of Rights Acquired under a Promise of Sale Agreement (S.L. 123.198)",
            "overview": "Assignments of Rights Acquired under a Promise of Sale Agreement (S.L. 123.198): Regulates assignment of property sale rights, tax treatment, documentation, and procedural requirements."
        },
        
        "sl_123_203": {
            "name": "UCA & Vacant Property (S.L. 123.203)",
            "overview": "UCA & Vacant Property (S.L. 123.203): Urban Conservation Area and vacant property tax provisions, rates, exemptions, and penalties under Income Tax Act."
        },
        
        # Subsidiary Legislation - Duty
        "sl_364_01": {
            "name": "Old Duty Exemptions (S.L. 364.01)",
            "overview": "Old Duty Exemptions (S.L. 364.01): Historical duty exemptions under Duty on Documents and Transfers Act."
        },
        
        "sl_364_06": {
            "name": "Duty on Documents and Transfers Rules (S.L. 364.06)",
            "overview": "Duty on Documents and Transfers Rules (S.L. 364.06): Detailed rules for stamp duty calculation, payment procedures, exemptions, and administrative processes."
        },
        
        "sl_364_12": {
            "name": "First Time Buyers & Gozo Exemptions (S.L. 364.12)",
            "overview": "First Time Buyers & Gozo Exemptions (S.L. 364.12): Stamp duty exemptions for first-time property buyers and properties in Gozo, eligibility criteria, and application procedures."
        },
        
        "sl_364_15": {
            "name": "Donation of Shares (S.L. 364.15)",
            "overview": "Donation of Shares (S.L. 364.15): Duty regulations for share donations, rates, exemptions, and procedural requirements."
        },
        
        "sl_364_17": {
            "name": "Second Time Buyers (S.L. 364.17)",
            "overview": "Second Time Buyers (S.L. 364.17): Stamp duty provisions for second-time property buyers, rates, and eligibility conditions."
        },
        
        "sl_364_18": {
            "name": "New Causa Mortis Interest Rate (S.L. 364.18)",
            "overview": "New Causa Mortis Interest Rate (S.L. 364.18): Interest rates for inheritance and succession duty calculations."
        },
        
        "sl_364_19": {
            "name": "UCA & Vacant Property (S.L. 364.19)",
            "overview": "UCA & Vacant Property (S.L. 364.19): Urban Conservation Area and vacant property duty provisions under stamp duty legislation."
        },
        
        # Subsidiary Legislation - Land Registration
        "sl_296_01": {
            "name": "Land Registration Rules (S.L. 296.01)",
            "overview": "Land Registration Rules (S.L. 296.01): Detailed procedures for land registration, forms, fees, timelines, and registry operations."
        },
        
        "sl_296_08": {
            "name": "Submission of Plans Rules (S.L. 296.08)",
            "overview": "Submission of Plans Rules (S.L. 296.08): Requirements for submitting architectural plans, surveys, and property documentation to land registry."
        },
        
        # Subsidiary Legislation - Prevention of Money Laundering
        "sl_373_01": {
            "name": "Prevention of Money Laundering Regulations (S.L. 373.01)",
            "overview": "Prevention of Money Laundering Regulations (S.L. 373.01): Detailed AML/CFT regulations including customer due diligence, record keeping, reporting, compliance programs, and supervisory requirements."
        },
        
        "sl_373_04": {
            "name": "Use of Cash (Restriction) Regulations (S.L. 373.04)",
            "overview": "Use of Cash (Restriction) Regulations (S.L. 373.04): Restrictions on cash transactions, limits, exemptions, reporting, and penalties for money laundering prevention."
        },
        
        # Subsidiary Legislation - Notarial
        "sl_55_01": {
            "name": "Functions & Duties of the Notarial College and Notarial Council (S.L. 55.01)",
            "overview": "Functions & Duties of the Notarial College and Notarial Council (S.L. 55.01): Governance structure, responsibilities, and procedures of notarial professional bodies."
        },
        
        "sl_55_05": {
            "name": "Acts of Deceased Notaries Regulations (S.L. 55.05)",
            "overview": "Acts of Deceased Notaries Regulations (S.L. 55.05): Procedures for managing notarial acts and archives of deceased notaries, custody, and access."
        },
        
        "sl_55_06": {
            "name": "Examination of Title Regulations (S.L. 55.06)",
            "overview": "Examination of Title Regulations (S.L. 55.06): Notarial duties and procedures for examining property titles, due diligence requirements, and liability standards."
        },
        
        "sl_55_07": {
            "name": "Notaries (Compulsory Insurance) Regulations (S.L. 55.07)",
            "overview": "Notaries (Compulsory Insurance) Regulations (S.L. 55.07): Professional indemnity insurance requirements for notaries, coverage amounts, and compliance obligations."
        },
        
        "sl_55_09": {
            "name": "Code of Ethics (S.L. 55.09)",
            "overview": "Code of Ethics (S.L. 55.09): Professional ethics code for notaries covering conduct standards, conflicts of interest, confidentiality, and professional responsibilities."
        },
        
        # Subsidiary Legislation - Public Registry
        "sl_56_03": {
            "name": "Public Registry (Inspection and Searches) Regulations (S.L. 56.03)",
            "overview": "Public Registry (Inspection and Searches) Regulations (S.L. 56.03): Procedures for public registry searches, document inspection, fees, and access rights."
        },
        
        # Subsidiary Legislation - Condominium
        "sl_398_01": {
            "name": "Condominium Regulations (S.L. 398.01)",
            "overview": "Condominium Regulations (S.L. 398.01): Detailed regulations for condominium administration, meetings, voting, maintenance, insurance, and dispute resolution."
        },
        
        # Subsidiary Legislation - Private Residential Leases
        "sl_604_02": {
            "name": "Registration of Private Residential Leases Contracts Regulations (S.L. 604.02)",
            "overview": "Registration of Private Residential Leases Contracts Regulations (S.L. 604.02): Mandatory lease registration procedures, forms, fees, penalties for non-registration, and compliance requirements."
        },
        
        # Subsidiary Legislation - AIP
        "sl_246_04": {
            "name": "AIP Values (S.L. 246.04)",
            "overview": "AIP Values (S.L. 246.04): Property valuation methodology and rates for Acquist Impost Proprium (property tax) assessment."
        },
        
        # Subsidiary Legislation - EPC
        "sl_623_01": {
            "name": "EPC Regulations (S.L. 623.01)",
            "overview": "EPC Regulations (S.L. 623.01): Energy Performance Certificate requirements for buildings, assessment procedures, validity, penalties, and compliance obligations."
        },
        
        # Civil Code Subsidiary Legislation
        "sl_16_14": {
            "name": "Termination of Mandates (S.L. 16.14)",
            "overview": "Termination of Mandates (S.L. 16.14): Regulations governing termination of mandates, agency relationships, and power of attorney under Civil Code."
        },
        
        # EU Regulations
        "eu_succession_regulation_650": {
            "name": "EU Succession Regulation - 650.2012",
            "overview": "EU Succession Regulation - 650.2012: European Union Regulation on jurisdiction, applicable law, recognition and enforcement of decisions, and cooperation in matters of succession, applicable in Malta."
        }
    }
    
    # Print summary
    print(f"\nDocuments in database: {len(documents)}")
    print(f"Metadata entries created: {len(metadata)}")
    print("\n" + "-"*80)
    print("DOCUMENT LIST WITH METADATA:")
    print("-"*80)
    
    for i, (doc_name, info) in enumerate(sorted(documents.items()), 1):
        doc_code = info['doc_code']
        chunks = info['chunk_count']
        has_metadata = doc_code in metadata
        status = "[OK]" if has_metadata else "[MISSING]"
        
        print(f"{i:2}. {status} {doc_name:<60} ({chunks:4} chunks)")
        if has_metadata:
            overview = metadata[doc_code]['overview']
            print(f"    {overview[:100]}...")
        print()
    
    # Save metadata to JSON
    output = {
        'metadata_entries': metadata,
        'documents_in_db': documents,
        'total_documents': len(documents),
        'total_chunks': sum(d['chunk_count'] for d in documents.values())
    }
    
    with open('document_metadata.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*80)
    print(f"[OK] Metadata saved to document_metadata.json")
    print(f"[OK] {len(metadata)} document overviews created")
    print(f"[OK] Covering {sum(d['chunk_count'] for d in documents.values())} total chunks")
    print("="*80)
    
    # Generate Python code for doc_processor.py
    print("\n[Python code for doc_processor.py]:\n")
    print("self.doc_overviews = {")
    for doc_code, meta in sorted(metadata.items()):
        print(f'    "{doc_code}": "{meta["overview"]}",')
    print("}")
    
    return metadata

if __name__ == "__main__":
    generate_document_metadata()

