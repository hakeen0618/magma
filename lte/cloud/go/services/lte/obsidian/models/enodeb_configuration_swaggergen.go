// Code generated by go-swagger; DO NOT EDIT.

package models

// This file was generated by the swagger tool.
// Editing this file might prove futile when you re-run the swagger generate command

import (
	"encoding/json"
	"strconv"

	strfmt "github.com/go-openapi/strfmt"

	"github.com/go-openapi/errors"
	"github.com/go-openapi/swag"
	"github.com/go-openapi/validate"
)

// EnodebConfiguration Configuration for an enodeB. Unfilled fields will be inherited from LTE network and gateway configuration.
// swagger:model enodeb_configuration
type EnodebConfiguration struct {

	// bandwidth mhz
	// Enum: [3 5 10 15 20]
	BandwidthMhz uint32 `json:"bandwidth_mhz,omitempty"`

	// cell id
	// Required: true
	// Maximum: 2.68435455e+08
	CellID *uint32 `json:"cell_id"`

	// device class
	// Required: true
	// Enum: [Baicells Nova-233 G2 OD FDD Baicells Nova-243 OD TDD Baicells Nova-246 OD FDD Baicells Neutrino 224 ID FDD Baicells Nova-436q TDD Baicells ID TDD/FDD NuRAN Cavium OC-LTE FreedomFi One]
	DeviceClass string `json:"device_class"`

	// earfcndl
	Earfcndl uint32 `json:"earfcndl,omitempty"`

	// ho algorithm config
	HoAlgorithmConfig *HoAlgorithmConfiguration `json:"ho_algorithm_config,omitempty"`

	// management server
	ManagementServer *ManagementServer `json:"managementServer,omitempty"`

	// mme pool 1
	// Format: ipv4
	MmePool1 strfmt.IPv4 `json:"mme_pool_1,omitempty"`

	// mme pool 2
	// Format: ipv4
	MmePool2 strfmt.IPv4 `json:"mme_pool_2,omitempty"`

	// neighbor cell list
	NeighborCellList []*NeighborCell `json:"neighbor_cell_list"`

	// neighbor frequency list
	NeighborFrequencyList []*NeighborFrequency `json:"neighbor_frequency_list"`

	// pci
	// Maximum: 503
	// Minimum: > 0
	Pci uint32 `json:"pci,omitempty"`

	// power control
	PowerControl *PowerControl `json:"power_control,omitempty"`

	// special subframe pattern
	// Maximum: 9
	SpecialSubframePattern uint32 `json:"special_subframe_pattern,omitempty"`

	// subframe assignment
	// Maximum: 6
	SubframeAssignment uint32 `json:"subframe_assignment,omitempty"`

	// sync 1588
	Sync1588 *Sync1588 `json:"sync_1588,omitempty"`

	// tac
	// Maximum: 65535
	// Minimum: 1
	Tac uint32 `json:"tac,omitempty"`

	// transmit enabled
	// Required: true
	TransmitEnabled *bool `json:"transmit_enabled"`

	// X2 status.
	X2EnableDisable *bool `json:"x2_enable_disable,omitempty"`
}

// Validate validates this enodeb configuration
func (m *EnodebConfiguration) Validate(formats strfmt.Registry) error {
	var res []error

	if err := m.validateBandwidthMhz(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateCellID(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateDeviceClass(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateHoAlgorithmConfig(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateManagementServer(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateMmePool1(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateMmePool2(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateNeighborCellList(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateNeighborFrequencyList(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validatePci(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validatePowerControl(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateSpecialSubframePattern(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateSubframeAssignment(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateSync1588(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateTac(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateTransmitEnabled(formats); err != nil {
		res = append(res, err)
	}

	if len(res) > 0 {
		return errors.CompositeValidationError(res...)
	}
	return nil
}

var enodebConfigurationTypeBandwidthMhzPropEnum []interface{}

func init() {
	var res []uint32
	if err := json.Unmarshal([]byte(`[3,5,10,15,20]`), &res); err != nil {
		panic(err)
	}
	for _, v := range res {
		enodebConfigurationTypeBandwidthMhzPropEnum = append(enodebConfigurationTypeBandwidthMhzPropEnum, v)
	}
}

// prop value enum
func (m *EnodebConfiguration) validateBandwidthMhzEnum(path, location string, value uint32) error {
	if err := validate.Enum(path, location, value, enodebConfigurationTypeBandwidthMhzPropEnum); err != nil {
		return err
	}
	return nil
}

func (m *EnodebConfiguration) validateBandwidthMhz(formats strfmt.Registry) error {

	if swag.IsZero(m.BandwidthMhz) { // not required
		return nil
	}

	// value enum
	if err := m.validateBandwidthMhzEnum("bandwidth_mhz", "body", m.BandwidthMhz); err != nil {
		return err
	}

	return nil
}

func (m *EnodebConfiguration) validateCellID(formats strfmt.Registry) error {

	if err := validate.Required("cell_id", "body", m.CellID); err != nil {
		return err
	}

	if err := validate.MaximumInt("cell_id", "body", int64(*m.CellID), 2.68435455e+08, false); err != nil {
		return err
	}

	return nil
}

var enodebConfigurationTypeDeviceClassPropEnum []interface{}

func init() {
	var res []string
	if err := json.Unmarshal([]byte(`["Baicells Nova-233 G2 OD FDD","Baicells Nova-243 OD TDD","Baicells Nova-246 OD FDD","Baicells Neutrino 224 ID FDD","Baicells Nova-436q TDD","Baicells ID TDD/FDD","NuRAN Cavium OC-LTE","FreedomFi One"]`), &res); err != nil {
		panic(err)
	}
	for _, v := range res {
		enodebConfigurationTypeDeviceClassPropEnum = append(enodebConfigurationTypeDeviceClassPropEnum, v)
	}
}

const (

	// EnodebConfigurationDeviceClassBaicellsNova233G2ODFDD captures enum value "Baicells Nova-233 G2 OD FDD"
	EnodebConfigurationDeviceClassBaicellsNova233G2ODFDD string = "Baicells Nova-233 G2 OD FDD"

	// EnodebConfigurationDeviceClassBaicellsNova243ODTDD captures enum value "Baicells Nova-243 OD TDD"
	EnodebConfigurationDeviceClassBaicellsNova243ODTDD string = "Baicells Nova-243 OD TDD"

	// EnodebConfigurationDeviceClassBaicellsNova246ODFDD captures enum value "Baicells Nova-246 OD FDD"
	EnodebConfigurationDeviceClassBaicellsNova246ODFDD string = "Baicells Nova-246 OD FDD"

	// EnodebConfigurationDeviceClassBaicellsNeutrino224IDFDD captures enum value "Baicells Neutrino 224 ID FDD"
	EnodebConfigurationDeviceClassBaicellsNeutrino224IDFDD string = "Baicells Neutrino 224 ID FDD"

	// EnodebConfigurationDeviceClassBaicellsNova436qTDD captures enum value "Baicells Nova-436q TDD"
	EnodebConfigurationDeviceClassBaicellsNova436qTDD string = "Baicells Nova-436q TDD"

	// EnodebConfigurationDeviceClassBaicellsIDTDDFDD captures enum value "Baicells ID TDD/FDD"
	EnodebConfigurationDeviceClassBaicellsIDTDDFDD string = "Baicells ID TDD/FDD"

	// EnodebConfigurationDeviceClassNuRANCaviumOCLTE captures enum value "NuRAN Cavium OC-LTE"
	EnodebConfigurationDeviceClassNuRANCaviumOCLTE string = "NuRAN Cavium OC-LTE"

	// EnodebConfigurationDeviceClassFreedomFiOne captures enum value "FreedomFi One"
	EnodebConfigurationDeviceClassFreedomFiOne string = "FreedomFi One"
)

// prop value enum
func (m *EnodebConfiguration) validateDeviceClassEnum(path, location string, value string) error {
	if err := validate.Enum(path, location, value, enodebConfigurationTypeDeviceClassPropEnum); err != nil {
		return err
	}
	return nil
}

func (m *EnodebConfiguration) validateDeviceClass(formats strfmt.Registry) error {

	if err := validate.RequiredString("device_class", "body", string(m.DeviceClass)); err != nil {
		return err
	}

	// value enum
	if err := m.validateDeviceClassEnum("device_class", "body", m.DeviceClass); err != nil {
		return err
	}

	return nil
}

func (m *EnodebConfiguration) validateHoAlgorithmConfig(formats strfmt.Registry) error {

	if swag.IsZero(m.HoAlgorithmConfig) { // not required
		return nil
	}

	if m.HoAlgorithmConfig != nil {
		if err := m.HoAlgorithmConfig.Validate(formats); err != nil {
			if ve, ok := err.(*errors.Validation); ok {
				return ve.ValidateName("ho_algorithm_config")
			}
			return err
		}
	}

	return nil
}

func (m *EnodebConfiguration) validateManagementServer(formats strfmt.Registry) error {

	if swag.IsZero(m.ManagementServer) { // not required
		return nil
	}

	if m.ManagementServer != nil {
		if err := m.ManagementServer.Validate(formats); err != nil {
			if ve, ok := err.(*errors.Validation); ok {
				return ve.ValidateName("managementServer")
			}
			return err
		}
	}

	return nil
}

func (m *EnodebConfiguration) validateMmePool1(formats strfmt.Registry) error {

	if swag.IsZero(m.MmePool1) { // not required
		return nil
	}

	if err := validate.FormatOf("mme_pool_1", "body", "ipv4", m.MmePool1.String(), formats); err != nil {
		return err
	}

	return nil
}

func (m *EnodebConfiguration) validateMmePool2(formats strfmt.Registry) error {

	if swag.IsZero(m.MmePool2) { // not required
		return nil
	}

	if err := validate.FormatOf("mme_pool_2", "body", "ipv4", m.MmePool2.String(), formats); err != nil {
		return err
	}

	return nil
}

func (m *EnodebConfiguration) validateNeighborCellList(formats strfmt.Registry) error {

	if swag.IsZero(m.NeighborCellList) { // not required
		return nil
	}

	for i := 0; i < len(m.NeighborCellList); i++ {
		if swag.IsZero(m.NeighborCellList[i]) { // not required
			continue
		}

		if m.NeighborCellList[i] != nil {
			if err := m.NeighborCellList[i].Validate(formats); err != nil {
				if ve, ok := err.(*errors.Validation); ok {
					return ve.ValidateName("neighbor_cell_list" + "." + strconv.Itoa(i))
				}
				return err
			}
		}

	}

	return nil
}

func (m *EnodebConfiguration) validateNeighborFrequencyList(formats strfmt.Registry) error {

	if swag.IsZero(m.NeighborFrequencyList) { // not required
		return nil
	}

	for i := 0; i < len(m.NeighborFrequencyList); i++ {
		if swag.IsZero(m.NeighborFrequencyList[i]) { // not required
			continue
		}

		if m.NeighborFrequencyList[i] != nil {
			if err := m.NeighborFrequencyList[i].Validate(formats); err != nil {
				if ve, ok := err.(*errors.Validation); ok {
					return ve.ValidateName("neighbor_frequency_list" + "." + strconv.Itoa(i))
				}
				return err
			}
		}

	}

	return nil
}

func (m *EnodebConfiguration) validatePci(formats strfmt.Registry) error {

	if swag.IsZero(m.Pci) { // not required
		return nil
	}

	if err := validate.MinimumInt("pci", "body", int64(m.Pci), 0, true); err != nil {
		return err
	}

	if err := validate.MaximumInt("pci", "body", int64(m.Pci), 503, false); err != nil {
		return err
	}

	return nil
}

func (m *EnodebConfiguration) validatePowerControl(formats strfmt.Registry) error {

	if swag.IsZero(m.PowerControl) { // not required
		return nil
	}

	if m.PowerControl != nil {
		if err := m.PowerControl.Validate(formats); err != nil {
			if ve, ok := err.(*errors.Validation); ok {
				return ve.ValidateName("power_control")
			}
			return err
		}
	}

	return nil
}

func (m *EnodebConfiguration) validateSpecialSubframePattern(formats strfmt.Registry) error {

	if swag.IsZero(m.SpecialSubframePattern) { // not required
		return nil
	}

	if err := validate.MaximumInt("special_subframe_pattern", "body", int64(m.SpecialSubframePattern), 9, false); err != nil {
		return err
	}

	return nil
}

func (m *EnodebConfiguration) validateSubframeAssignment(formats strfmt.Registry) error {

	if swag.IsZero(m.SubframeAssignment) { // not required
		return nil
	}

	if err := validate.MaximumInt("subframe_assignment", "body", int64(m.SubframeAssignment), 6, false); err != nil {
		return err
	}

	return nil
}

func (m *EnodebConfiguration) validateSync1588(formats strfmt.Registry) error {

	if swag.IsZero(m.Sync1588) { // not required
		return nil
	}

	if m.Sync1588 != nil {
		if err := m.Sync1588.Validate(formats); err != nil {
			if ve, ok := err.(*errors.Validation); ok {
				return ve.ValidateName("sync_1588")
			}
			return err
		}
	}

	return nil
}

func (m *EnodebConfiguration) validateTac(formats strfmt.Registry) error {

	if swag.IsZero(m.Tac) { // not required
		return nil
	}

	if err := validate.MinimumInt("tac", "body", int64(m.Tac), 1, false); err != nil {
		return err
	}

	if err := validate.MaximumInt("tac", "body", int64(m.Tac), 65535, false); err != nil {
		return err
	}

	return nil
}

func (m *EnodebConfiguration) validateTransmitEnabled(formats strfmt.Registry) error {

	if err := validate.Required("transmit_enabled", "body", m.TransmitEnabled); err != nil {
		return err
	}

	return nil
}

// MarshalBinary interface implementation
func (m *EnodebConfiguration) MarshalBinary() ([]byte, error) {
	if m == nil {
		return nil, nil
	}
	return swag.WriteJSON(m)
}

// UnmarshalBinary interface implementation
func (m *EnodebConfiguration) UnmarshalBinary(b []byte) error {
	var res EnodebConfiguration
	if err := swag.ReadJSON(b, &res); err != nil {
		return err
	}
	*m = res
	return nil
}
