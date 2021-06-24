from collections import defaultdict
from typing import Any, List, Tuple, Optional

from flask import current_app
from sqlalchemy.orm import Session

from cidc_api.config.db import BaseModel

identity = lambda v: v
cimac_id_to_cimac_participant_id = lambda cimac_id: cimac_id[:7]


class MetadataModel(BaseModel):
    __abstract__ = True

    def unique_field_values(self) -> Optional[Tuple[Any]]:
        unique_field_values = []
        for column in self.__table__.columns:
            # column.primary_key == True for 1+ column guaranteed
            if column.unique or column.primary_key:
                value = getattr(self, column.name)
                unique_field_values.append(value)

        if all(v is None for v in unique_field_values):
            return None  # special value

        return tuple(unique_field_values)

    def merge(self, other):
        """Merge column values from other into self, raising an error on conflicts between non-null fields."""
        if self.__class__ != other.__class__:
            raise Exception(
                f"cannot merge {self.__class__} instance with {other.__class__} instance"
            )

        for column in self.__table__.columns:
            current = getattr(self, column.name)
            incoming = getattr(other, column.name)
            if current is None:
                setattr(self, column.name, incoming)
            elif incoming is not None and current != incoming:
                raise Exception(
                    f"found conflicting values for {self.__tablename__}.{column.name}: {current}!={other}"
                )


###### ALL MODEL DEFINITIONS SHOULD GO ABOVE THIS LINE ######
def _get_global_insertion_order() -> List[MetadataModel]:
    """
    Produce an ordering of all metadata model types based on foreign key dependencies
    between models. For a given model, all models it depends on are guaranteed to
    appear before it in this list.
    """
    models = MetadataModel.__subclasses__()

    # Build a dictionary mapping table names to model classes -
    # we use this below to look up the model classes associated with
    # a given foreign key.
    table_to_model = {m.__tablename__: m for m in models}

    # Build two graphs representing foreign-key relationships between models:
    # - fks_to_parents, mapping models to the set of models they depend on
    # - parents_to_fks, mapping models to the set of models that depend on them
    fks_to_parents = defaultdict(set)
    parent_to_fks = defaultdict(set)
    for model in models:
        for fk in model.__table__.foreign_keys:
            fk_model = table_to_model.get(fk.column.table.name)
            parent_to_fks[model].add(fk_model)
            fks_to_parents[fk_model].add(model)

    # Topologically sort the dependency graph to produce a valid insertion order
    # using Kahn's algorithm: https://en.wikipedia.org/wiki/Topological_sorting#Kahn's_algorithm
    ordered_models = []
    depless_models = set(
        model for model in models if len(model.__table__.foreign_keys) == 0
    )
    while len(depless_models) > 0:
        model = depless_models.pop()
        ordered_models.append(model)
        for fk_model in fks_to_parents[model]:
            fks = parent_to_fks[fk_model]
            fks.remove(model)
            if len(fks) == 0:
                depless_models.add(fk_model)

    return ordered_models


def insert_record_batch(
    records: List[MetadataModel],
    session: Optional[Session] = None,
    dry_run: bool = False,
) -> List[Exception]:
    """
    Try to insert the given list of models into the database in a single transaction,
    rolling back and returning a list of errors if any are encountered. If `dry_run` is `True`,
    rollback the transaction regardless of whether any errors are encountered.
    """
    if session is None:
        session = current_app.extensions["sqlalchemy"].db.session

    errors = []
    for record in records:
        try:
            with session.begin_nested():
                session.add(record)
        except Exception as e:
            errors.append(e)

    if dry_run or len(errors):
        session.rollback()
    else:
        session.commit()

    return errors