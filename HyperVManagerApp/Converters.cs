using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.UI.Xaml.Data;

namespace HyperVManager
{
    public class BytesToMBConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, string language)
        {
            if (value is long bytes)
            {
                return (bytes / (1024.0 * 1024.0)).ToString("F2"); // Convert to MB with 2 decimal places
            }
            return value;
        }

        public object ConvertBack(object value, Type targetType, object parameter, string language)
        {
            throw new NotImplementedException();
        }
    }

    public class StringListConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, string language)
        {
            if (value is List<string> list)
            {
                return string.Join(", ", list);
            }
            return value;
        }

        public object ConvertBack(object value, Type targetType, object parameter, string language)
        {
            throw new NotImplementedException();
        }
    }
}
