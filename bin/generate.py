from rdflib import ConjunctiveGraph, Namespace, BNode, Literal, RDF, URIRef
from testdata import PATIENTS_FILE
import ontology_service 
from patient import Patient
from med import Med
from problem import Problem
from procedure import Procedure
from refill import Refill
from vitals import VitalSigns
from immunization import Immunization
from lab import Lab
from allergy import Allergy
from clinicalnote import ClinicalNote
from socialhistory import SocialHistory
from familyhistory import FamilyHistory
import argparse
import sys
import os
from common.rdf_tools.util import *

# Some constant strings:
FILE_NAME_TEMPLATE = "p%s.xml"  # format for output files: p<patient id>.xml

SP_DEMOGRAPHICS = "http://smartplatforms.org/records/%s/demographics"
RXN_URI="http://purl.bioontology.org/ontology/RXNORM/%s"
NUI_URI="http://purl.bioontology.org/ontology/NDFRT/%s"
UNII_URI="http://fda.gov/UNII/%s"
SNOMED_URI="http://purl.bioontology.org/ontology/SNOMEDCT/%s"
LOINC_URI="http://purl.bioontology.org/ontology/LNC/%s"

# First Declare Name Spaces
SP = Namespace("http://smartplatforms.org/terms#")
SPCODE = Namespace("http://smartplatforms.org/terms/codes/")
DC = Namespace("http://purl.org/dc/elements/1.1/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
RDFS=Namespace("http://www.w3.org/2000/01/rdf-schema#")
VCARD=Namespace("http://www.w3.org/2006/vcard/ns#")


class PatientGraph:
   """ Represents a patient's RDF graph"""

   def codedValue(self,codeclass,uri,title,system,identifier):
     """ Adds a CodedValue to the graph and returns node"""
     cvNode=BNode()
     self.g.add((cvNode,RDF.type,SP.CodedValue))
     self.g.add((cvNode,DCTERMS['title'],Literal(title)))

     cNode=URIRef(uri)
     self.g.add((cvNode,SP['code'], cNode))

     # Two types:  the general "Code" and specific, e.g. "BloodPressureCode"
     self.g.add((cNode,RDF.type,codeclass))
     self.g.add((cNode,RDF.type,SP['Code']))

     self.g.add((cNode,DCTERMS['title'],Literal(title)))
     self.g.add((cNode, SP['system'], Literal(system)))
     self.g.add((cNode, DCTERMS['identifier'], Literal(identifier)))
     return cvNode

   def valueAndUnit(self,value,units):
     """Adds a ValueAndUnit node to a graph; returns the node"""
     vNode = BNode()
     self.g.add((vNode,RDF.type,SP['ValueAndUnit']))
     self.g.add((vNode,SP['value'],Literal(value)))
     self.g.add((vNode,SP['unit'],Literal(units)))
     return vNode

   def __init__(self,p):
      """Create an instance of a RDF graph for patient instance p""" 
      self.pid=p.pid
      # Create a RDF graph and namespaces:
      g = ConjunctiveGraph()
      self.g = g  # Keep a reference to this graph as an instance var

      # BindNamespaces to the graph:
      g.bind('rdfs',RDFS)
      g.bind('sp',SP)
      g.bind('spcode', SPCODE)
      g.bind('dc',DC)
      g.bind('dcterms',DCTERMS)
      g.bind('foaf',FOAF)
      g.bind('v',VCARD)

      self.patient = BNode()
      g.add((self.patient,RDF.type,SP.MedicalRecord))

      # Now add the patient demographic triples:
      pNode = BNode()
      self.addStatement(pNode)
      g.add((pNode,RDF.type,SP.Demographics))

      nameNode = BNode()
      g.add((pNode, VCARD['n'], nameNode))
      g.add((nameNode,RDF.type, VCARD['Name']))
      g.add((nameNode,VCARD['given-name'],Literal(p.fname)))
      g.add((nameNode,VCARD['family-name'],Literal(p.lname)))
      
      if len(p.initial) > 0:
         g.add((nameNode,VCARD['additional-name'],Literal(p.initial)))

      if len(p.pcode) > 0:
          addrNode = BNode() 
          g.add((pNode, VCARD['adr'], addrNode))
          g.add((addrNode, RDF.type, VCARD['Address']))
          g.add((addrNode, RDF.type, VCARD['Home']))
          g.add((addrNode, RDF.type, VCARD['Pref']))
          g.add((addrNode,VCARD['street-address'],Literal(p.street)))
          if len(p.apartment) > 0: g.add((addrNode,VCARD['extended-address'],Literal(p.apartment)))
          g.add((addrNode,VCARD['locality'],Literal(p.city)))
          g.add((addrNode,VCARD['region'],Literal(p.region)))
          g.add((addrNode,VCARD['postal-code'],Literal(p.pcode)))
          g.add((addrNode,VCARD['country'],Literal(p.country)))

      if len(p.home) > 0:
          homePhoneNode = BNode() 
          g.add((pNode, VCARD['tel'], homePhoneNode))
          g.add((homePhoneNode, RDF.type, VCARD['Tel']))
          g.add((homePhoneNode, RDF.type, VCARD['Home']))
          g.add((homePhoneNode, RDF.type, VCARD['Pref']))
          g.add((homePhoneNode,RDF.value,Literal(p.home)))
      
      if len(p.cell) > 0:
          cellPhoneNode = BNode() 
          g.add((pNode, VCARD['tel'], cellPhoneNode))
          g.add((cellPhoneNode, RDF.type, VCARD['Tel']))
          g.add((cellPhoneNode, RDF.type, VCARD['Cell']))
          if len(p.home) == 0: g.add((cellPhoneNode, RDF.type, VCARD['Pref']))
          g.add((cellPhoneNode,RDF.value,Literal(p.cell)))
          
      if len(p.gestage) > 0:
          gestAge = BNode() 
          g.add((pNode, SP['gestationalAgeAtBirth'], gestAge))
          g.add((gestAge, RDF.type, SP['ValueAndUnit']))
          g.add((gestAge,SP['value'],Literal(p.gestage)))
          g.add((gestAge,SP['unit'],Literal("wk")))
      
      g.add((pNode,FOAF['gender'],Literal(p.gender)))
      g.add((pNode,VCARD['bday'],Literal(p.dob)))
      
      if len(p.email) > 0:
          g.add((pNode,VCARD['email'],Literal(p.email)))

      recordNode = BNode()
      g.add((pNode,SP['medicalRecordNumber'],recordNode))
      g.add((recordNode, RDF.type, SP['Code']))
      g.add((recordNode, DCTERMS['title'], Literal("My Hospital Record %s"%p.pid)))
      g.add((recordNode, DCTERMS['identifier'], Literal(p.pid)))
      g.add((recordNode, SP['system'], Literal("My Hospital Record")))
      
   def addStatement(self, s):
      self.g.add((self.patient,SP.hasStatement, s))
      self.g.add((s,SP.belongsTo, self.patient))

   def addMedList(self):
      """Adds a MedList to a patient's graph"""

      g = self.g
      if not self.pid in Med.meds: return  # No meds for this patient
      for m in Med.meds[self.pid]:
        mNode = BNode()
        g.add((mNode,RDF.type,SP['Medication']))
        g.add((mNode,SP['drugName'],self.codedValue(SPCODE["RxNorm_Semantic"], RXN_URI%m.rxn,m.name,RXN_URI%"",m.rxn)))
        g.add((mNode,SP['startDate'],Literal(m.start)))
        if len(m.end) > 0:
            g.add((mNode,SP['endDate'],Literal(m.end))) 
        g.add((mNode,SP['instructions'],Literal(m.sig))) 
        if m.qtt:
          g.add((mNode,SP['quantity'],self.valueAndUnit(m.qtt,m.qttunit)))
        if m.freq:
          g.add((mNode,SP['frequency'],self.valueAndUnit(m.freq,m.frequnit)))

        self.addStatement(mNode)

        # Now,loop through and add fulfillments for each med
        for fill in Refill.refill_list(m.pid,m.rxn):
          rfNode = BNode()
          g.add((rfNode,RDF.type,SP['Fulfillment']))
          g.add((rfNode,DCTERMS['date'],Literal(fill.date)))
          g.add((rfNode,SP['quantityDispensed'], self.valueAndUnit(fill.q,"{tab}")))

          g.add((rfNode,SP['dispenseDaysSupply'],Literal(fill.days)))

          g.add((rfNode,SP['medication'],mNode)) # create bidirectional links
          g.add((mNode,SP['fulfillment'],rfNode))
          self.addStatement(rfNode)

   def addClinicalNotes(self):
      """Add notes to a patient's graph"""
      g = self.g
      if not self.pid in ClinicalNote.clinicalNotes: return # No notes to add
      for note in ClinicalNote.clinicalNotes[self.pid]:
        self.addStatement(note.triples((None, RDF.type, SP['ClinicalNote'])).next()[0])
        g += note

   def addSocialHistory(self):
      """Add social history to a patient's graph"""
      if not self.pid in SocialHistory.socialHistories: return # No social history

      g = self.g
      sh = SocialHistory.socialHistories[self.pid]
      smokingStatus = ontology_service.coded_value(g,URIRef(SNOMED_URI%sh.smokingStatusCode))
      
      hnode = BNode()
      g.add((hnode,RDF.type,SP['SocialHistory']))
      g.add((hnode,SP['smokingStatus'],smokingStatus))

      self.addStatement(hnode)

   def addFamilyHistory(self):
      """Add family history to a patient's graph"""
      if not self.pid in FamilyHistory.familyHistories: return # No family history
      g = self.g
      for fh in FamilyHistory.familyHistories[self.pid]:
        fhnode = BNode()
        g.add((fhnode,RDF.type,SP['FamilyHistory']))
        g.add((fhnode,SP['aboutRelative'],
            self.codedValue(SPCODE["SNOMED"],SNOMED_URI%fh.relativecode,fh.relativetitle,SNOMED_URI%"",fh.relativecode)))
        if len(fh.dateofbirth) > 0:
            g.add((fhnode,SP['dateOfBirth'],Literal(fh.dateofbirth)))
        if len(fh.dateofdeath) > 0:
            g.add((fhnode,SP['dateOfDeath'],Literal(fh.dateofdeath)))
        if len(fh.problemcode) > 0:
            g.add((fhnode,SP['hasProblem'],
                self.codedValue(SPCODE["SNOMED"],SNOMED_URI%fh.problemcode,fh.problemtitle,SNOMED_URI%"",fh.problemcode)))
        if len(fh.heightcm) > 0:
            for vt in VitalSigns.vitalTypes:
                if vt['name'] == 'height':
                    hnode = BNode()
                    g.add((hnode, sp.value, Literal(fh.heightcm)))
                    g.add((hnode, RDF.type, sp.VitalSign))
                    g.add((hnode, sp.unit, Literal(vt['unit'])))
                    g.add((hnode, sp.vitalName, ontology_service.coded_value(g, URIRef(vt['uri']))))
                    g.add((fhnode, sp[vt['predicate']], hnode))
                    break
        self.addStatement(fhnode)

   def addProblemList(self):
      """Add problems to a patient's graph"""
      g = self.g
      if not self.pid in Problem.problems: return # No problems to add
      for prob in Problem.problems[self.pid]:
        pnode = BNode()
        g.add((pnode,RDF.type,SP['Problem']))
        g.add((pnode,SP['startDate'],Literal(prob.start)))
        if len(prob.end) > 0:
            g.add((pnode,SP['endDate'],Literal(prob.end)))        
        g.add((pnode,SP['problemName'],
            self.codedValue(SPCODE["SNOMED"],SNOMED_URI%prob.snomed,prob.name,SNOMED_URI%"",prob.snomed)))
        self.addStatement(pnode)

   def addProcedureList(self):
      """Add procedures to a patient's graph"""
      g = self.g
      if not self.pid in Procedure.procedures: return
      for proc in Procedure.procedures[self.pid]:
        pnode = BNode()
        g.add((pnode,RDF.type,SP['Procedure']))
        g.add((pnode,dcterms.date, Literal(proc.date)))
        g.add((pnode,SP['procedureName'],
            self.codedValue(SPCODE["SNOMED"],SNOMED_URI%proc.snomed,proc.name,SNOMED_URI%"",proc.snomed)))
        g.add((pnode,SP['notes'], Literal(proc.notes)))
        self.addStatement(pnode)

   def addVitalSigns(self):
      """Add vitals to a patient's graph"""
      g = self.g
      if not self.pid in VitalSigns.vitals: return # No vitals to add

      for v in VitalSigns.vitals[self.pid]:
        vnode = BNode()
        self.addStatement(vnode)
        g.add((vnode,RDF.type,SP['VitalSignSet']))
        g.add((vnode,dcterms.date, Literal(v.timestamp)))

        enode = BNode()
        g.add((enode,RDF.type,SP['Encounter']))
        g.add((vnode,SP.encounter, enode))
        g.add((enode,SP.startDate, Literal(v.start_date)))
        g.add((enode,SP.endDate, Literal(v.end_date)))

        if v.encounter_type == 'ambulatory':
            etype = ontology_service.coded_value(g, URIRef("http://smartplatforms.org/terms/codes/EncounterType#ambulatory"))
            g.add((enode, SP.encounterType, etype))
        
        def attachVital(vt, p):
            ivnode = BNode()
            if hasattr(v, vt['name']):
                val = getattr(v, vt['name'])
                if val and len(val) > 0:
                    g.add((ivnode, sp.value, Literal(val)))
                    g.add((ivnode, RDF.type, sp.VitalSign))
                    g.add((ivnode, sp.unit, Literal(vt['unit'])))
                    g.add((ivnode, sp.vitalName, ontology_service.coded_value(g, URIRef(vt['uri']))))
                    g.add((p, sp[vt['predicate']], ivnode))
            return ivnode

        for vt in VitalSigns.vitalTypes:
            attachVital(vt, vnode)

        if v.systolic:
            bpnode = BNode()
            g.add((vnode, sp.bloodPressure, bpnode))
            g.add((bpnode, RDF.type, sp.BloodPressure))
            attachVital(VitalSigns.systolic, bpnode)
            attachVital(VitalSigns.diastolic, bpnode)
            
        self.addStatement(vnode)

   def addImmunizations(self):
      """Add immunizations to a patient's graph"""

      g = self.g

      if not self.pid in Immunization.immunizations: return # No immunizations to add

      for i in Immunization.immunizations[self.pid]:

        inode = BNode()
        self.addStatement(inode)
        g.add((inode,RDF.type,SP['Immunization']))
        g.add((inode,dcterms.date, Literal(i.date)))
        g.add((inode, sp.administrationStatus, ontology_service.coded_value(g, URIRef(i.administration_status))))

        if i.refusal_reason:
            g.add((inode, sp.refusalReason, ontology_service.coded_value(g, URIRef(i.refusal_reason))))

        cvx_system, cvx_id = i.cvx.rsplit("#",1)
        g.add((inode, sp.productName, self.codedValue(SPCODE["ImmunizationProduct"],URIRef(i.cvx), i.cvx_title, cvx_system+"#", cvx_id)))

        if (i.vg):
            vg_system, vg_id = i.vg.rsplit("#",1)
            g.add((inode, sp.productClass, self.codedValue(SPCODE["ImmunizationClass"],URIRef(i.vg), i.vg_title, vg_system+"#", vg_id)))

        if (i.vg2):
            vg2_system, vg2_id = i.vg2.rsplit("#",1)
            g.add((inode, sp.productClass, self.codedValue(SPCODE["ImmunizationClass"],URIRef(i.vg2), i.vg2_title, vg2_system+"#", vg2_id)))

   def addLabResults(self):
       """Adds Lab Results to the patient's graph"""
       g = self.g
       if not self.pid in Lab.results: return  #No labs
       for lab in Lab.results[self.pid]:
         lNode = BNode()
         g.add((lNode,RDF.type,SP['LabResult']))
         g.add((lNode,SP['labName'],
            self.codedValue(SPCODE["LOINC"], LOINC_URI%lab.code,lab.name,LOINC_URI%"",lab.code)))

         if lab.scale=='Qn':
           qNode = BNode()
           g.add((qNode,RDF.type,SP['QuantitativeResult']))
           g.add((qNode,SP['valueAndUnit'],
             self.valueAndUnit(lab.value,lab.units)))

           if len(lab.low) > 0 and len(lab.high) > 0:
               # Add Range Values
               rNode = BNode()
               g.add((rNode,RDF.type,SP['ValueRange']))
               g.add((rNode,SP['minimum'],
                       self.valueAndUnit(lab.low,lab.units)))
               g.add((rNode,SP['maximum'],
                       self.valueAndUnit(lab.high,lab.units)))
               g.add((qNode,SP['normalRange'],rNode)) 
               
           g.add((lNode,SP['quantitativeResult'],qNode))

         else:  
           qNode = BNode()
           g.add((qNode,RDF.type,SP['NarrativeResult']))
           g.add((qNode,SP['value'],Literal(lab.value)))
           g.add((lNode,SP['narrativeResult'],qNode))

         g.add((lNode,dcterms.date, Literal(lab.date)))
         g.add((lNode,SP['accessionNumber'],Literal(lab.acc_num)))      

   def addAllergies(self):
        """Add allergies to a patient's graph"""

        g = self.g

        if not self.pid in Allergy.allergies: return # No allergies to add

        for a in Allergy.allergies[self.pid]:
            if a.statement == 'negative':
                aExcept = BNode()
                g.add((aExcept,RDF.type,SP['AllergyExclusion']))
                g.add((aExcept,SP['allergyExclusionName'], self.codedValue(SPCODE["AllergyExclusion"],SNOMED_URI%a.code,a.allergen,SNOMED_URI%'',a.code)))
                g.add((aExcept,dcterms.date,Literal(a.start)))
                self.addStatement(aExcept)
            else:
                aNode = BNode()
                g.add((aNode,RDF.type,SP['Allergy']))
                g.add((aNode,SP['severity'], self.codedValue(SPCODE["AllergySeverity"],SNOMED_URI%a.severity_code,a.severity,SNOMED_URI%'',a.severity_code)))
                g.add((aNode,SP['allergicReaction'], self.codedValue(SPCODE["SNOMED"],SNOMED_URI%a.snomed,a.reaction,SNOMED_URI%'',a.snomed)))
                g.add((aNode,SP['startDate'],Literal(a.start)))
                if len(a.end) > 0:
                    g.add((aNode,SP['endDate'],Literal(a.end)))   
                
                if a.type == 'drugClass':
                    g.add((aNode,SP['category'], self.codedValue(SPCODE["AllergyCategory"],SNOMED_URI%'416098002','drug allergy', SNOMED_URI%'','416098002')))
                    g.add((aNode,SP['drugClassAllergen'],
                    self.codedValue(SPCODE["NDFRT"],NUI_URI%a.code,a.allergen,NUI_URI%''.split('&')[0], a.code)))
                elif a.type == 'drug':
                    g.add((aNode,SP['category'], self.codedValue(SPCODE["AllergyCategory"],SNOMED_URI%'416098002','drug allergy', SNOMED_URI%'','416098002')))
                    g.add((aNode,SP['drugAllergen'],
                    self.codedValue(SPCODE["RxNorm_Ingredient"],RXN_URI%a.code,a.allergen,RXN_URI%'', a.code)))
                elif a.type == 'food':
                    g.add((aNode,SP['category'], self.codedValue(SPCODE["AllergyCategory"],SNOMED_URI%'414285001','food allergy',SNOMED_URI%'','414285001')))
                    g.add((aNode,SP['otherAllergen'], self.codedValue(SPCODE["UNII"],UNII_URI%a.code,a.allergen,UNII_URI%'',a.code)))
                elif a.type == 'environmental':
                    g.add((aNode,SP['category'], self.codedValue(SPCODE["AllergyCategory"],SNOMED_URI%'426232007','environmental allergy',SNOMED_URI%'','426232007')))
                    g.add((aNode,SP['otherAllergen'], self.codedValue(SPCODE["UNII"],UNII_URI%a.code,a.allergen,UNII_URI%'',a.code)))
                
                self.addStatement(aNode)

   def toRDF(self,format="xml"):
         return self.g.serialize(format=format)

def initData():
   """Load data and mappings from Raw data files and mapping files"""
   Patient.load()
   Med.load()
   Problem.load()
   Lab.load()
   Refill.load()
   VitalSigns.load()
   Immunization.load()
   Procedure.load()
   SocialHistory.load()
   FamilyHistory.load()
   ClinicalNote.load()
   Allergy.load()

def writePatientGraph(f,pid,format):
   """Writes a patient's RDF out to a file, f"""
   p = Patient.mpi[pid]
   g = PatientGraph(p)
   g.addMedList()
   g.addProblemList()
   g.addProcedureList()
   g.addSocialHistory()
   g.addFamilyHistory()
   g.addClinicalNotes()
   g.addLabResults()
   g.addAllergies()
   g.addVitalSigns()
   g.addImmunizations()
   print >>f, g.toRDF(format=format)


def displayPatientSummary(pid):
   """writes a patient summary to stdout"""
   if not pid in Patient.mpi: return
   print Patient.mpi[pid].asTabString()
   print "PROBLEMS: ",
   if not pid in Problem.problems: print "None",
   else: 
     for prob in Problem.problems[pid]: print prob.name+"; ",
   print "\nMEDICATIONS: ",
   if not pid in Med.meds: print "None",
   else:
     for med in Med.meds[pid]: 
       print med.name+"{%d}; "%len(Refill.refill_list(pid,med.rxn)),
   print "\nLABS: ",
   if not pid in Lab.results: print "None",
   else:
     print "%d results"%len(Lab.results[pid])
   print "\n"

if __name__=='__main__':

  parser = argparse.ArgumentParser(description='Test Data Generator')
  group = parser.add_mutually_exclusive_group()
  group.add_argument('--summary', metavar='pid',nargs='?', const="all", 
     help="displays patient summary (default is 'all')")
  parser.add_argument('--rdf-format', metavar='rdf_format', nargs='?', default='xml',
          help='RDF serialization format to use (defaults to "xml". Also allowed: "turtle".)')
  group.add_argument('--rdf', metavar='pid', nargs='?', const='1520204',
     help='display RDF for a patient (default=1520204)')
  group.add_argument('--write', metavar='dir', nargs='?', const='.',
     help="writes all patient RDF files to directory dir (default='.')")
  group.add_argument('--write-indivo',dest='writeIndivo', metavar='dir', nargs='?', const='.',
     help="writes patient XML files to an Indivo sample data directory dir (default='.')")
  group.add_argument('--patients', action='store_true',
         help='Generates new patient data file (overwrites existing one)')

  args = parser.parse_args()

  # Print a patient summary: 
  if args.summary:
    initData()
    if args.summary=='all': # Print a summary of all patients
      for pid in Patient.mpi: displayPatientSummary(pid)
      parser.exit()
    else: # Just print a single patient's summary
      if not args.summary in Patient.mpi:
        parser.error("Patient ID = %s not found"%args.summary)
      else: displayPatientSummary(args.summary)
    parser.exit()
 
  # Display a single patient's RDF
  if args.rdf:
    initData()
    if not args.rdf in Patient.mpi:
      parser.error("Patient ID = %s not found."%args.rdf)
    else:
      writePatientGraph(sys.stdout,args.rdf, args.rdf_format)
      parser.exit()
 
  # Write all patient RDF files out to a directory
  if args.write:
    print "Writing files to %s:"%args.write
    initData()
    path = args.write
    if not os.path.exists(path):
      parser.error("Invalid path: '%s'.Path must already exist."%path)
    if not path.endswith('/'): path = path+'/' # Works with DOS? Who cares??
    for pid in Patient.mpi:
      f = open(path+FILE_NAME_TEMPLATE%pid,'w')
      writePatientGraph(f,pid,args.rdf_format)
      f.close()
      # Show progress with '.' characters
      print ".", 
      sys.stdout.flush()
    parser.exit(0,"\nDone writing %d patient RDF files!"%len(Patient.mpi))

  # Write all patient RDF files out to a directory
  if args.writeIndivo:
    print "Writing files to %s:"%args.writeIndivo
    initData()
    path = args.writeIndivo
    if not os.path.exists(path):
      parser.error("Invalid path: '%s'.Path must already exist."%path)

    import indivo

    for pid in Patient.mpi:
      indivo.IndivoSamplePatient(pid, path).writePatientData()
      sys.stdout.flush()
    parser.exit(0,"Done writing %d patient data profiles!\n"%len(Patient.mpi))

  # Generate a new patients data file, re-randomizing old names, dob, etc:
  Patient.generate()  
  parser.exit(0,"Patient data written to: %s\n"%PATIENTS_FILE)

  parser.error("No arguments given")
