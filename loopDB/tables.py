from partsdb.system.Tables import Base, BaseMixIn, PartMixIn, AnnotationMixIn
from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

from Bio.SeqRecord import SeqRecord
from Bio.SeqFeature import SeqFeature, FeatureLocation
from Bio.Alphabet import IUPAC
from Bio.Seq import Seq

class NameMixIn(object):
	name		=		Column(String(100), unique = True)

class RE(Base, BaseMixIn, NameMixIn):
	seq			=		Column( String(10) )
	@hybrid_property
	def rcSeq(self):
		swap = {'A':'T', 'T':'A', 'G':'C', 'C':'G'}
		return ''.join( [ swap[letter] for letter in self.seq ] )[::-1]

class RES(Base, BaseMixIn, NameMixIn):
	site5		=		Column( String(10) )
	site3		=		Column( String(10) )
	re			=		relationship( 'RE' )
	reID 		=		Column(Integer, ForeignKey('re.id'))

class BaseSeq(Base, BaseMixIn, PartMixIn, NameMixIn):
	receiver	=		relationship( 'RES' )
	receiverID	=		Column(Integer, ForeignKey('res.id'))
	features	=		relationship("BaseFeature", backref = "baseSeq")

	@hybrid_property
	def record(self):
		features = []
		for feature in self.features:
			seqFeature = SeqFeature( FeatureLocation( feature.start, feature.end, strand = 1 if feature.forward else -1 ), type = feature.type, qualifiers = {'label' : feature.label, "ApEinfo_fwdcolor" : feature.color, "ApEinfo_revcolor" : feature.color}  )
			features.append(seqFeature)
		return SeqRecord( id = self.dbid, seq = Seq( self.seq, IUPAC.unambiguous_dna ), name = self.name, features = features, description = "Generated by LoopDB" )

class Backbone(Base, BaseMixIn, NameMixIn):
	baseSeq		=		relationship( 'BaseSeq', backref = 'backbones' )
	baseSeqID	=		Column(Integer, ForeignKey('baseseq.id'))

	adapter		=		relationship( 'RES' )
	adapterID	=		Column(Integer, ForeignKey('res.id'))

	@hybrid_property
	def seq(self):
		return 	self.adapter.site3 + self.adapter.re.rcSeq +\
				self.baseSeq.seq +\
				self.adapter.re.seq + self.adapter.site5

	@hybrid_property
	def record(self):
		return Seq( self.adapter.site3 ) + Seq(self.adapter.re.rcSeq) +\
				self.baseSeq.record +\
				Seq(self.adapter.re.seq) + Seq(self.adapter.site5)

class Partship(Base):
	__tablename__ = 'partship'
	parentID	=		Column(Integer, ForeignKey('part.id'), primary_key = True)
	childID		=		Column(Integer, ForeignKey('part.id'), primary_key = True)

	child		=		relationship( "Part", backref = "parentShips", foreign_keys = [childID] )
	parent		=		relationship( "Part", backref = "childShips", foreign_keys = [parentID] )

	pos			=		Column(Integer)

class Part(Base, BaseMixIn, PartMixIn, NameMixIn):
	id			=		Column(Integer, primary_key=True)

	backbone	=		relationship( 'Backbone' )
	backboneID	=		Column( Integer, ForeignKey('backbone.id'))

	features	=		relationship("Feature", backref = "part")

	@hybrid_property
	def children(self):
		return [ childShip.child for childShip in sorted(self.childShips, key = lambda x: x.pos) ]

	@hybrid_method
	def __len__(self):
		if not self.children:
			return len(self.partSeq)
		else:
			return sum( [ len(child) for child in self.children ] )

	@hybrid_property
	def level(self):
		if not self.children:
			return 0
		else:
			return max( [ child.level for child in self.children ] ) + 1

	@hybrid_property
	def sites(self):
		return [self.backbone.adapter.site5, self.backbone.adapter.site3]

	@hybrid_property
	def receiverSites(self):
		return [self.backbone.baseSeq.receiver.site5, self.backbone.baseSeq.receiver.site3]

	@hybrid_property
	def partSeq(self):
		if self.children:
			seq = self.receiverSites[0] + self.children[0].partSeq
			for i in range( len(self.children)-1):
				child = self.children[i+1]
				seq += child.backbone.adapter.site5 + child.partSeq

			return seq + self.receiverSites[1]
		else:
			return self.seq

	@hybrid_property
	def fullSeq(self):
		return self.partSeq + self.backbone.seq

	@hybrid_property
	def record(self):
		if self.children:
			record = Seq(self.receiverSites[0]) + self.children[0].record
			for i in range( len(self.children)-1 ):
				child = self.children[i+1]
				record += Seq(child.backbone.adapter.site5) + child.record
			record += Seq( self.receiverSites[1] )
			record.name = self.name
			record.id = self.dbid
			record.description = "Generated by LoopDB"
			return record
		else:
			features = []
			for feature in self.features:
				seqFeature = SeqFeature( FeatureLocation( feature.start, feature.end, strand = 1 if feature.forward else -1 ), type = feature.type, qualifiers = {'label' : feature.label, "ApEinfo_fwdcolor" : feature.color, "ApEinfo_revcolor" : feature.color}  )
				features.append(seqFeature)
			return SeqRecord( id = self.dbid, seq = Seq( self.seq, IUPAC.unambiguous_dna ), name = self.name, features = features, description = "Generated by LoopDB" )

	@hybrid_property
	def fullRecord(self):
		record = self.record + self.backbone.record
		record.seq.alphabet = IUPAC.unambiguous_dna
		return record

class Feature(Base, BaseMixIn):
	partID		=		Column( Integer, ForeignKey("part.id") )

	label		=		Column( String(100) )
	type		=		Column( String(100) )
	start		=		Column( Integer )
	end			=		Column( Integer )

	forward		=		Column( Boolean )
	color		=		Column( String(20) )

class BaseFeature(Base, BaseMixIn):
	baseSeqID	=		Column( Integer, ForeignKey("baseseq.id") )

	label		=		Column( String(100) )
	type		=		Column( String(100) )
	start		=		Column( Integer )
	end			=		Column( Integer )

	forward		=		Column( Boolean )
	color		=		Column( String(20) )