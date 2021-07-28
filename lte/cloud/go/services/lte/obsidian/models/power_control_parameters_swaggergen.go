// Code generated by go-swagger; DO NOT EDIT.

package models

// This file was generated by the swagger tool.
// Editing this file might prove futile when you re-run the swagger generate command

import (
	strfmt "github.com/go-openapi/strfmt"

	"github.com/go-openapi/errors"
	"github.com/go-openapi/swag"
	"github.com/go-openapi/validate"
)

// PowerControlParameters Power Contorl Parameters Configuration for eNodeb devices.
// swagger:model PowerControlParameters
type PowerControlParameters struct {

	// pa
	Pa int32 `json:"pa,omitempty"`

	// pb
	// Maximum: 3
	// Minimum: 0
	Pb *uint32 `json:"pb,omitempty"`

	// reference signal power
	ReferenceSignalPower int32 `json:"reference_signal_power,omitempty"`
}

// Validate validates this power control parameters
func (m *PowerControlParameters) Validate(formats strfmt.Registry) error {
	var res []error

	if err := m.validatePb(formats); err != nil {
		res = append(res, err)
	}

	if len(res) > 0 {
		return errors.CompositeValidationError(res...)
	}
	return nil
}

func (m *PowerControlParameters) validatePb(formats strfmt.Registry) error {

	if swag.IsZero(m.Pb) { // not required
		return nil
	}

	if err := validate.MinimumInt("pb", "body", int64(*m.Pb), 0, false); err != nil {
		return err
	}

	if err := validate.MaximumInt("pb", "body", int64(*m.Pb), 3, false); err != nil {
		return err
	}

	return nil
}

// MarshalBinary interface implementation
func (m *PowerControlParameters) MarshalBinary() ([]byte, error) {
	if m == nil {
		return nil, nil
	}
	return swag.WriteJSON(m)
}

// UnmarshalBinary interface implementation
func (m *PowerControlParameters) UnmarshalBinary(b []byte) error {
	var res PowerControlParameters
	if err := swag.ReadJSON(b, &res); err != nil {
		return err
	}
	*m = res
	return nil
}
