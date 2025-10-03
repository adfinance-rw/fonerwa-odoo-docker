# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrAppraisalRatingScale(models.Model):
    _name = 'hr.appraisal.rating.scale'
    _description = 'Performance Rating Scale'
    _order = 'min_score desc'

    name = fields.Char(string='Rating Name', required=True)
    min_score = fields.Float(string='Minimum Score', required=True)
    max_score = fields.Float(string='Maximum Score', required=True)
    color = fields.Char(string='Color Code', required=True, default='#808080')
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)

    @api.constrains('min_score', 'max_score')
    def _check_score_range(self):
        for record in self:
            if record.min_score >= record.max_score:
                raise ValidationError("Minimum score must be less than maximum score.")
            if record.min_score < 0 or record.max_score > 100:
                raise ValidationError("Scores must be between 0 and 100.")

    @api.model
    def get_rating_for_score(self, score):
        """Get the rating scale for a given score"""
        if not score:
            return False
        
        rating = self.search([
            ('min_score', '<=', score),
            ('max_score', '>=', score)
        ], limit=1)
        
        return rating

    @api.model
    def create_default_scales(self):
        """Create default rating scales"""
        scales = [
            {
                'name': 'Exceptional Performer',
                'min_score': 86,
                'max_score': 100,
                'color': '#28a745',  # Green
                'description': 'Consistently exceeds expectations and demonstrates exceptional performance',
                'sequence': 1
            },
            {
                'name': 'Out Performer',
                'min_score': 76,
                'max_score': 85,
                'color': '#007bff',  # Blue
                'description': 'Frequently exceeds expectations and shows strong performance',
                'sequence': 2
            },
            {
                'name': 'Solid Performer',
                'min_score': 66,
                'max_score': 75,
                'color': '#e83e8c',  # Purple/Pink
                'description': 'Consistently meets expectations and shows solid performance',
                'sequence': 3
            },
            {
                'name': 'Developing Performer',
                'min_score': 51,
                'max_score': 65,
                'color': '#ffc107',  # Yellow/Orange
                'description': 'Sometimes meets expectations, has potential for improvement',
                'sequence': 4
            },
            {
                'name': 'Under Performer',
                'min_score': 1,
                'max_score': 50,
                'color': '#dc3545',  # Red
                'description': 'Rarely meets expectations, requires significant improvement',
                'sequence': 5
            }
        ]
        
        for scale_data in scales:
            existing = self.search([('name', '=', scale_data['name'])], limit=1)
            if not existing:
                self.create(scale_data)
