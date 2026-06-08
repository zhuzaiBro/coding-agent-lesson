"""step4: Component contract specification schema."""
from typing import List, Optional

from pydantic import BaseModel, Field


class PropSpec(BaseModel):
    name: str = Field(description="Prop name (camelCase, e.g. articles, onSave)")
    type: str = Field(description="TypeScript type definition (e.g. 'Article[]', 'boolean')")
    description: str = Field(description="Prop purpose description")
    required: bool = Field(description="Whether this prop is required")


class EventParam(BaseModel):
    name: str
    type: str


class EventSpec(BaseModel):
    name: str = Field(description="Event name (onXxx, e.g. onNavigate, onChange)")
    description: str = Field(description="When the event is triggered")
    parameters: Optional[List[EventParam]] = Field(default=None, description="Callback function parameters")


class ComponentSpec(BaseModel):
    componentId: str = Field(description="Unique component ID (PascalCase), must have specific business meaning")
    originalId: str = Field(description="Original component ID from UI Schema for traceability")
    type: str = Field(description="Component type (e.g. Table, Form, Navbar)")
    description: str = Field(description="Business logic the component must implement")
    props: List[PropSpec] = Field(description="Props received by the component")
    events: List[EventSpec] = Field(description="Events exposed by the component")
    dataDependencies: List[str] = Field(description="Data model IDs this component depends on")
    shadcnComponent: Optional[str] = Field(default=None, description="Base Shadcn component to build on")


class ComponentResult(BaseModel):
    components: List[ComponentSpec] = Field(description="List of business components to generate")
