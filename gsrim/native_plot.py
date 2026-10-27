"""Native Qt scientific charts inspired by the supplied TRIM bitmap style."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class ScientificPlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        self.tracks = None
        self.language = "zh"
        self.empty_text = None
        self.setMinimumSize(480, 380)
        self.setAutoFillBackground(True)

    def set_data(self, data, tracks=None, language="zh", empty_text=None):
        self.data, self.tracks, self.language = data, tracks, language
        self.empty_text = empty_text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        self.draw(painter, self.width(), self.height())
        painter.end()

    def image(self, width=1500, height=1050):
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.white)
        painter = QPainter(image)
        self.draw(painter, width, height)
        painter.end()
        return image

    def draw(self, painter, width, height):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(0, 0, width, height, Qt.GlobalColor.white)
        scale = max(.72, min(width/800, height/620))
        def font(size=11, bold=False, serif=False):
            value = QFont("Times New Roman" if serif else "Microsoft YaHei UI")
            value.setPointSizeF(size*scale)
            value.setBold(bold)
            return value
        painter.setPen(QColor("#1c2630"))
        if self.data is None:
            painter.setFont(font(15, True))
            painter.drawText(QRectF(0,0,width,height), Qt.AlignmentFlag.AlignCenter,
                self.empty_text or ("开始计算或载入结果后显示图表" if self.language == "zh" else "Run a simulation or load results to display a chart"))
            return
        d = self.data
        left, right = 105*scale, 100*scale
        plot_width=max(100,width-left-right)
        statistics=getattr(d,"statistics",[])
        # Place the four moments above the legend in SRIM's two-column layout.
        painter.setFont(font(10,True))
        legend_x=left+12*scale
        legend_y=(120 if statistics else 70)*scale
        legend=[]
        for label,values,color,fill in d.series:
            label_width=painter.fontMetrics().horizontalAdvance(label)
            item_width=label_width+65*scale
            if legend_x>left+12*scale and legend_x+item_width>left+plot_width:
                legend_x=left+12*scale;legend_y+=23*scale
            legend.append((legend_x,legend_y,label,label_width,color))
            legend_x+=item_width
        notes_y=legend_y+18*scale
        top=max((150 if statistics else 112)*scale,
                notes_y+18*scale*len(d.notes[:2])+12*scale)
        bottom = 90*scale
        box = QRectF(left, top, plot_width, max(100,height-top-bottom))
        painter.setFont(font(21,True,self.language != "zh"))
        painter.drawText(QRectF(left,15*scale,box.width(),38*scale), Qt.AlignmentFlag.AlignCenter,d.title)
        # Red outer frame, black axes, gray horizontal grid: the reference style.
        painter.setPen(QPen(QColor("#e00000"),1.2*scale))
        painter.drawRect(QRectF(left-3*scale,9*scale,box.width()+6*scale,box.bottom()-5*scale))
        if statistics:
            painter.setPen(QColor("#1233c8"))
            moment_font=font(11,True,self.language!="zh")
            painter.setFont(moment_font)
            column_width=(box.width()-36*scale)/2
            longest=max(painter.fontMetrics().horizontalAdvance(f"{label}  =  {value}")
                        for label,value in statistics)
            if longest>column_width:
                moment_font.setPointSizeF(moment_font.pointSizeF()*column_width/longest)
                painter.setFont(moment_font)
            for i,(label,value) in enumerate(statistics[:4]):
                column,row=divmod(i,2)
                x=left+12*scale+column*(column_width+12*scale)
                painter.drawText(QRectF(x,(59+row*24)*scale,column_width,24*scale),
                                 Qt.AlignmentFlag.AlignVCenter,f"{label}  =  {value}")
        painter.setFont(font(10,True))
        for legend_x,legend_y,label,label_width,color in legend:
            painter.setPen(QPen(QColor(color),2*scale))
            painter.drawLine(QPointF(legend_x,legend_y),QPointF(legend_x+23*scale,legend_y))
            painter.drawText(QRectF(legend_x+30*scale,legend_y-12*scale,label_width+5*scale,24*scale),
                             Qt.AlignmentFlag.AlignVCenter,label)
        painter.setPen(QColor("#1233c8"))
        painter.setFont(font(9))
        for i,note in enumerate(d.notes[:2]):
            painter.drawText(QRectF(left+12*scale,notes_y+i*18*scale,box.width()-24*scale,20*scale),
                             Qt.AlignmentFlag.AlignVCenter,note)
        xmax = max(d.xmax or max(d.x,default=1), 1e-30)
        xmin = 0.
        if self.tracks is not None:
            vals = [point[0] for track in self.tracks for point in track]
            zvals = [point[2] for track in self.tracks for point in track]
            ymin, ymax = min(vals,default=-1), max(vals,default=1)
            pad=max((ymax-ymin)*.08,1)
            ymin-=pad; ymax+=pad
            xmax=max(xmax,max(zvals,default=xmax))
        else:
            ymin=0.
            ymax = max((max((float(v) for v in values if math.isfinite(float(v))), default=0)
                        for _,values,_,_ in d.series),default=0)
            if ymax <= 0:
                ymax = 1.
            # Round the upper grid limit to a readable value.
            magnitude=10**math.floor(math.log10(ymax))
            ymax=math.ceil(ymax*1.07/magnitude*2)*magnitude/2
        X=lambda value: box.left()+(value-xmin)/(xmax-xmin)*box.width()
        Y=lambda value: box.bottom()-(value-ymin)/(ymax-ymin)*box.height()
        painter.save()
        painter.setClipRect(box)
        if self.tracks is not None:
            colors=["#e00000","#d63428","#1742cc","#1a8a59"]
            for i,track in enumerate(self.tracks):
                if len(track)<2:continue
                path=QPainterPath(QPointF(X(track[0][2]),Y(track[0][0])))
                for point in track[1:]:path.lineTo(X(point[2]),Y(point[0]))
                painter.setPen(QPen(QColor(colors[i%len(colors)]),.9*scale))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)
        else:
            for label,values,color,fill in d.series:
                points=[(float(x),float(y)) for x,y in zip(d.x,values) if math.isfinite(float(x)) and math.isfinite(float(y))]
                if not points:continue
                curve=QPainterPath()
                gap=(points[1][0]-points[0][0])/2 if len(points)>1 else xmax/2
                curve.moveTo(X(points[0][0]-gap),Y(points[0][1]))
                for x,y in points:
                    curve.lineTo(X(x-gap),Y(y))
                    curve.lineTo(X(x+gap),Y(y))
                if fill:
                    area=QPainterPath(curve)
                    area.lineTo(X(points[-1][0]+gap),Y(0))
                    area.lineTo(X(points[0][0]-gap),Y(0))
                    area.closeSubpath()
                    painter.fillPath(area,QColor(color))
                painter.setPen(QPen(QColor(color),1.4*scale))
                painter.drawPath(curve)
        painter.restore()
        painter.setFont(font(9,False,True))
        for i in range(7):
            value=ymin+(ymax-ymin)*i/6
            y=Y(value)
            painter.setPen(QPen(QColor("#8a8a8a"),.7*scale))
            painter.drawLine(QPointF(box.left(),y),QPointF(box.right(),y))
            painter.setPen(QColor("#000000"))
            label=f"{value:.3g}" if abs(value)<1e4 else f"{value:.1e}"
            painter.drawText(QRectF(box.right()+10*scale,y-11*scale,right-14*scale,22*scale),
                             Qt.AlignmentFlag.AlignVCenter,label)
        for i in range(7):
            value=xmax*i/6
            x=X(value)
            painter.setPen(QColor("#000000"))
            painter.drawLine(QPointF(x,box.bottom()),QPointF(x,box.bottom()-7*scale))
            painter.drawText(QRectF(x-45*scale,box.bottom()+9*scale,90*scale,24*scale),
                             Qt.AlignmentFlag.AlignCenter,f"{value:.5g}")
        for boundary in d.boundaries:
            painter.setPen(QPen(QColor("#5a6e77"),scale,Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(X(boundary),box.top()),QPointF(X(boundary),box.bottom()))
        painter.setPen(QPen(Qt.GlobalColor.black,scale))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(box)
        painter.setFont(font(12,True,self.language != "zh"))
        painter.drawText(QRectF(left,box.bottom()+43*scale,box.width(),30*scale),
                         Qt.AlignmentFlag.AlignCenter,d.xlabel)
        painter.save()
        painter.translate(30*scale,box.center().y())
        painter.rotate(-90)
        painter.setFont(font(11,True,self.language != "zh"))
        painter.drawText(QRectF(-box.height()/2,-20*scale,box.height(),35*scale),
                         Qt.AlignmentFlag.AlignCenter,d.ylabel)
        painter.restore()
