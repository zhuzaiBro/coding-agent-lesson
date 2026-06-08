"""step3: UI architecture analysis schema."""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    # Layout & Containers
    Layout = "Layout"
    Card = "Card"
    Sheet = "Sheet"
    Dialog = "Dialog"
    ScrollArea = "ScrollArea"
    ResizablePanel = "ResizablePanel"
    Accordion = "Accordion"
    Collapsible = "Collapsible"
    Separator = "Separator"
    AspectRatio = "AspectRatio"
    # Navigation
    Navbar = "Navbar"
    Sidebar = "Sidebar"
    NavigationMenu = "NavigationMenu"
    Tabs = "Tabs"
    Breadcrumb = "Breadcrumb"
    Menubar = "Menubar"
    DropdownMenu = "DropdownMenu"
    # Data Display
    Table = "Table"
    List = "List"
    Grid = "Grid"
    Avatar = "Avatar"
    Badge = "Badge"
    Carousel = "Carousel"
    Chart = "Chart"
    HoverCard = "HoverCard"
    Tooltip = "Tooltip"
    Popover = "Popover"
    # Form & Interaction
    Form = "Form"
    Button = "Button"
    Input = "Input"
    Textarea = "Textarea"
    Select = "Select"
    Checkbox = "Checkbox"
    RadioGroup = "RadioGroup"
    Switch = "Switch"
    Slider = "Slider"
    Toggle = "Toggle"
    ToggleGroup = "ToggleGroup"
    DatePicker = "DatePicker"
    InputOTP = "InputOTP"
    Label = "Label"
    Toolbar = "Toolbar"
    Editor = "Editor"
    # Feedback
    Alert = "Alert"
    AlertDialog = "AlertDialog"
    Progress = "Progress"
    Skeleton = "Skeleton"
    Toaster = "Toaster"
    ContextMenu = "ContextMenu"


class SectionRole(str, Enum):
    navigation = "navigation"
    filter = "filter"
    list = "list"
    detail = "detail"
    editor = "editor"
    dashboard = "dashboard"
    form = "form"


class SectionLayout(str, Enum):
    flex_row = "flex-row"
    flex_col = "flex-col"
    grid = "grid"
    single = "single"


class PageLayout(str, Enum):
    default = "default"
    dashboard_shell = "dashboard-shell"
    blank = "blank"
    editor_shell = "editor-shell"


class UIComponent(BaseModel):
    id: str = Field(description="Component ID (PascalCase)")
    type: ComponentType = Field(description="Component type")
    label: str = Field(description="Component display label")
    bindDataModel: str = Field(description="Bound data model ID")
    bindBehavior: List[str] = Field(description="Bound behavior IDs")


class UISection(BaseModel):
    sectionId: str = Field(description="Section ID")
    role: SectionRole = Field(description="Section functional role")
    layout: SectionLayout = Field(description="Section internal layout")
    title: str = Field(description="Section title")
    components: List[UIComponent] = Field(description="Components in this section")


class UIPage(BaseModel):
    pageId: str = Field(description="Corresponding Capability PageID")
    route: str = Field(description="Route path (e.g. /articles/[id], /dashboard)")
    description: str = Field(description="Page visual/functional description")
    layout: PageLayout = Field(description="Overall page layout skeleton")
    sections: List[UISection] = Field(description="Main sections on the page")


class UIResult(BaseModel):
    pages: List[UIPage] = Field(description="All page structure designs")
    themeStrategy: str = Field(description="Theme strategy based on design analysis")
