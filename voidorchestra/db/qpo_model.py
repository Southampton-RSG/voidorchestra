#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the QPO models, made up of components, used in synthetic lightcurve generation.
"""
from typing import Any, Dict, List

import astropy.units as u
import numpy as np
from astropy.modeling import Model
from astropy.time import TimeDelta
from astropy.units import Quantity
from mind_the_gaps.models.psd_models import SHO, BendingPowerlaw, Lorentzian
from sqlalchemy import Double, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from voidorchestra.db import Base, LightcurveSynthetic


class QPOModel(Base):  # pylint: disable=too-few-public-methods
    """
    ORM class for QPO models used for synthetic lightcurve generation.

    These are models, either stand-alone or collections of other models.

    Attributes
    ----------
    qpo_model_id: integer
        A unique ID for the QPO model.
    qpo_model_parent_id: integer
        The parent, if any, of this model component.
    name: string
        A name describing the model.
    polymorphic_type: string
        The polymorphic name type.
    lightcurves: relationship
        The lightcurves generated using this model.
    qpo_model_parent: relationship
        The QPO model that is this model's parent, if any.
    coherence: float
    period_value: float
        The value of the period.
    period_format: string
        The format of the period.
    variance_fraction: float
    """
    __tablename__: str = "qpo_model"
    __mapper_args__: Dict[str, str] = {
        "polymorphic_on": "polymorphic_type",
    }

    qpo_model_id: Mapped[int] = mapped_column(primary_key=True)
    qpo_model_parent_id: Mapped[int] = mapped_column(ForeignKey("qpo_model.qpo_model_id"))
    name: Mapped[str] = mapped_column(String(32))
    polymorphic_type: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    model: Mapped[str] = mapped_column(String(32))
    coherence: Mapped[float] = mapped_column(Float())
    variance_fraction: Mapped[float] = mapped_column(Float())
    period_value: Mapped[float] = mapped_column(Double())
    period_format: Mapped[str] = mapped_column(String(16))

    qpo_model_parent: Mapped['QPOModel'] = relationship(
        remote_side=qpo_model_parent_id, uselist=False,
        backref=backref("qpo_model_children", remote_side=qpo_model_id, uselist=True)
    )
    lightcurves: List[Mapped[LightcurveSynthetic]] = relationship(back_populates="qpo_model")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.qpo_model_id})"

    def get_model_for_mean_rate(
            self,
            rate_mean: Quantity[u.s**-1]
    ) -> Model:
        """
        For a mean lightcurve count rate, generate a model that can be passed to MindTheGaps.

        Parameters
        ----------
        rate_mean: float
            Mean light curve count.

        Returns
        -------
        A Mind the Gaps model.
        """
        raise NotImplementedError("This is an abstract model.")

    def get_period(self) ->  TimeDelta:
        """
        Gets the period, in whatever unit it was saved in.

        Returns
        -------
        Quantity:
            The period, as a quantity.
        """
        return TimeDelta(self.period_value, format=self.period_format)


class QPOModelComposite(QPOModel):
    """
    Wrapper for the SHO model from Mind the Gaps.
    """
    __mapper_args__: Dict[str, str] = {
        "polymorphic_identity": "composite",
    }

    def add_components(
            self,
            components: List[Dict[str, Any]]
    ) -> 'QPOModelComposite':
        """
        Adds sub-components to this composite model.

        Parameters
        ----------
        components: List[Dict[str, Any]
            The children to add to the model.

        Returns
        -------
        QPOModelComposite
            Self, for chaining methods.
        """
        for idx, component in enumerate(components):
            component['model'](
                name=f"{self.name} component: {idx}",
                qpo_model_parent=self,
                **component['arguments'],
            )

        return self

    def get_model_for_mean_rate(self, rate_mean: Quantity[u.s**-1]) -> Model:
        """
        Sums the models defining this as their parent, and returns them.

        Parameters
        ----------
        rate_mean: float
            Mean light curve count.

        Returns
        -------
        A Mind the Gaps model.
        """
        qpo_model: QPOModel = self.qpo_model_children[0].get_model_for_mean_rate(rate_mean)

        for qpo_model_add in self.qpo_model_children[1:]:
            qpo_model_add += qpo_model.get_model_for_mean_rate(rate_mean)

        return qpo_model


class QPOModelSHO(QPOModel):
    """
    Wrapper for the SHO model from Mind the Gaps.
    """
    __mapper_args__: Dict[str, str] = {
        'polymorphic_identity': 'mind_the_gaps_sho',
    }

    def get_model_for_mean_rate(self, rate_mean: Quantity[u.s**-1]) -> Model:
        """
        For a mean lightcurve count rate, generate a model that can be passed to MindTheGaps.

        Parameters
        ----------
        rate_mean: float
            Mean light curve count.

        Returns
        -------
        A Mind the Gaps model.
        """
        return SHO(
            omega0=2.0 * np.pi / self.get_period().to(u.s).value,
            Q=self.coherence,
            S0=self.variance_fraction**2.0 * rate_mean.to(u.s**-1).value ** 2,
        )


class QPOModelLorentzian(QPOModel):
    """
    Wrapper for the Lorentzian model from Mind the Gaps.
    """
    __mapper_args__: Dict[str, str] = {
        'polymorphic_identity': 'mind_the_gaps_lorentzian',
    }

    def get_model_for_mean_rate(self, rate_mean: Quantity[u.s**-1]) -> Model:
        """
        For a mean lightcurve count rate, generate a model that can be passed to MindTheGaps.

        Parameters
        ----------
        rate_mean: float
            Mean light curve count.

        Returns
        -------
        A Mind the Gaps model.
        """
        return Lorentzian(
            omega0=2.0 * np.pi / self.get_period().to(u.s).value,
            Q=self.coherence,
            S0=self.variance_fraction**2.0 * rate_mean.to(u.s**-1).value ** 2,
        )


class QPOModelBPL(QPOModel):
    """
    Wrapper for the Bending Powerlaw model from Mind the Gaps.
    """
    __mapper_args__: Dict[str, str] = {
        'polymorphic_identity': 'mind_the_gaps_bpl',
    }

    def get_model_for_mean_rate(self, rate_mean: Quantity[u.s**-1]) -> Model:
        """
        For a mean lightcurve count rate, generate a model that can be passed to MindTheGaps.

        Parameters
        ----------
        rate_mean: float
            Mean light curve count.

        Returns
        -------
        A Mind the Gaps model.
        """
        return BendingPowerlaw(
            omega0=2.0 * np.pi / self.get_period().to(u.s).value,
            Q=self.coherence,
            S0=self.variance_fraction**2.0 * rate_mean.to(u.s**-1).value ** 2,
        )
